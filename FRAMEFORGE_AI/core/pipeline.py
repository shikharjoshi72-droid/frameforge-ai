"""Workflow orchestration: chunking -> per-chunk LLM extraction -> merge -> registers -> story analysis."""
from ai.nvidia_client import NvidiaError
from core import production_planner, scene_extractor, screenplay_analyzer
from core.chunking_engine import build_chunks, segment
from core.text_preprocessor import clean_pages


class PipelineError(Exception):
    pass


def prepare(repo, pid, settings) -> int:
    doc = repo.latest_document(pid)
    if not doc:
        raise PipelineError("Upload a screenplay first.")
    pages = clean_pages(doc["pages"])
    blocks, info = segment(pages)
    if not blocks:
        raise PipelineError("No scene content could be identified in the document.")
    chunks = build_chunks(blocks, settings.chunk_max_chars, settings.chunk_max_blocks, settings.context_chars)
    repo.reset_chunks(pid, [c.to_payload() for c in chunks])
    basis = "estimated" if any("estimated" in w for w in doc["warnings"]) else "actual"
    repo.update_analysis(pid, segmentation=info, page_count=len(pages), block_count=len(blocks), page_basis=basis)
    repo.set_stage(pid, "chunking", "DONE", f"{len(blocks)} scene blocks in {len(chunks)} chunks "
                                            f"({info['headings_found']} headings detected)")
    return len(chunks)


def run_chunks(repo, pid, client, progress=None) -> dict:
    rows = [r for r in repo.list_chunks(pid) if r["status"] != "DONE"]
    done = failed = 0
    repo.set_stage(pid, "scene_extraction", "RUNNING", f"{len(rows)} chunk(s) to process")
    for i, row in enumerate(rows, 1):
        try:
            result = scene_extractor.extract_chunk(client, row["payload"])
            repo.set_chunk(pid, row["chunk_id"], "DONE", result)
            done += 1
            status = "DONE"
        except NvidiaError as exc:
            repo.set_chunk(pid, row["chunk_id"], "FAILED", error=str(exc))
            failed += 1
            status = "FAILED"
            if exc.fatal:
                if progress:
                    progress(i, len(rows), row["chunk_id"], status)
                repo.set_stage(pid, "scene_extraction", "FAILED", str(exc))
                return {"done": done, "failed": failed + len(rows) - i, "fatal": str(exc)}
        except Exception as exc:  # keep going; the chunk can be retried
            repo.set_chunk(pid, row["chunk_id"], "FAILED", error=f"{exc.__class__.__name__}: {exc}")
            failed += 1
            status = "FAILED"
        if progress:
            progress(i, len(rows), row["chunk_id"], status)
    repo.set_stage(pid, "scene_extraction", "FAILED" if failed else "DONE",
                   f"{done} chunk(s) done, {failed} failed")
    return {"done": done, "failed": failed, "fatal": None}


def assemble(repo, pid) -> dict:
    rows = repo.list_chunks(pid)
    if not rows:
        raise PipelineError("No chunks prepared.")
    pending = [r["chunk_id"] for r in rows if r["status"] != "DONE"]
    if pending:
        raise PipelineError(f"{len(pending)} chunk(s) are not complete ({', '.join(pending[:5])}); retry them first.")
    scenes, char_infos, summaries = scene_extractor.merge_chunks(rows)
    repo.replace_scenes(pid, scenes)
    repo.update_analysis(pid, char_infos=char_infos, summaries=summaries)
    production_planner.rebuild_registers(repo, pid)
    repo.set_stage(pid, "registers", "DONE", f"{len(scenes)} scenes, registers built")
    return {"scenes": len(scenes), "flagged": sum(1 for s in scenes if s["needs_review"])}


def run_story(repo, pid, client) -> dict:
    meta = repo.get_analysis(pid)
    repo.set_stage(pid, "story_analysis", "RUNNING")
    try:
        result = screenplay_analyzer.analyze_story(client, meta.get("summaries", []), repo.list_scenes(pid),
                                                   meta.get("page_count", 0), meta.get("page_basis", "actual"))
    except Exception as exc:
        repo.set_stage(pid, "story_analysis", "FAILED", str(exc))
        raise
    repo.update_analysis(pid, **result)
    repo.set_stage(pid, "story_analysis", "DONE", "Story analysis saved")
    return result


def analyse(repo, pid, client, settings, progress=None, fresh=True) -> dict:
    """fresh=True restarts from the stored screenplay; fresh=False only retries incomplete chunks."""
    if fresh:
        prepare(repo, pid, settings)
    stats = run_chunks(repo, pid, client, progress)
    out = {"chunks": stats, "assembled": None, "story": None, "errors": []}
    if stats.get("fatal"):
        out["errors"].append(stats["fatal"])
        return out
    if stats["failed"] == 0 and (stats["done"] > 0 or not repo.list_scenes(pid)):
        out["assembled"] = assemble(repo, pid)
        try:
            run_story(repo, pid, client)
            out["story"] = "DONE"
        except Exception as exc:
            out["errors"].append(f"Story analysis failed (scenes were saved): {exc}")
    elif stats["failed"]:
        out["errors"].append(f"{stats['failed']} chunk(s) failed; successful chunks are saved. Retry the failed chunks.")
    return out
