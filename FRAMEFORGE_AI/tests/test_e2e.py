import os
import tempfile

from config.settings import get_settings
from core import blackbook_generator, pipeline, production_planner
from core.schedule_generator import generate_schedule
from database.repository import Repository
from tests.helpers import FakeClient, make_script


def _repo_with_script(text):
    repo = Repository(os.path.join(tempfile.mkdtemp(), "t.db"))
    pid = repo.create_project("Test Film", genre="Drama")
    lines = text.split("\n")
    pages = ["\n".join(lines[i:i + 50]) for i in range(0, len(lines), 50)]
    repo.add_document(pid, "screenplay", "s.txt", "abc", len(text), len(pages), "", text, pages, ["Page numbers are estimated"])
    return repo, pid


def test_sample_script_full_pipeline_and_pdf():
    text = open(os.path.join(os.path.dirname(__file__), "data", "sample_short.txt")).read()
    repo, pid = _repo_with_script(text)
    st = get_settings()
    out = pipeline.analyse(repo, pid, FakeClient(drop_block="B003"), st)
    assert out["assembled"]["scenes"] == 7, out
    scenes = repo.list_scenes(pid)
    assert [s["scene_number"] for s in scenes] == [str(i) for i in range(1, 8)]       # order + numbering
    assert scenes[0]["heading"] == "INT. COFFEE SHOP - DAY" and scenes[0]["time_of_day"] == "DAY"
    assert "GHOST" not in scenes[0]["characters"] and "GHOST" in scenes[0]["review_reason"]  # hallucination removed + flagged
    assert scenes[2]["needs_review"] and "no data" in scenes[2]["review_reason"]       # dropped block flagged, not invented
    assert "MAN IN COAT" not in sum((s["characters"] for s in scenes), [])             # O.S. voice is not 'present'
    assert any(m.startswith("MAN IN COAT") for m in scenes[4]["mentioned"])
    assert scenes[5]["time_of_day"] == "CONTINUOUS"
    assert all(i["name"].lower() != "camera" for s in scenes for i in s["equipment"])  # generic gear filtered
    chars = {c["name"].upper(): c for c in repo.list_characters(pid)}
    assert chars["MAYA"]["appearances"] == sum(1 for s in scenes if "MAYA" in s["characters"])  # Python-counted
    locs = {l["name"] for l in repo.list_locations(pid)}
    assert {"Old Cinema", "Coffee Shop", "Beach"} <= locs
    # schedule -> approve -> call sheet -> persistence across a fresh Repository -> PDF
    res = generate_schedule(scenes, "2026-12-01")
    repo.save_schedule(pid, res["days"])
    repo.set_schedule_approved(pid, True)
    repo2 = Repository(repo.path)
    assert len(repo2.list_shooting_days(pid)) == len(res["days"]) and repo2.get_project(pid)["schedule_approved"] == 1
    repo2.set_scene_status(scenes[0]["id"], "Completed")
    bb = blackbook_generator.generate(repo2, pid)
    v = bb["verification"]
    assert v["ok"] and v["pages"] >= 10 and not v["missing"], v
    assert bb["bytes"][:5] == b"%PDF-"
    assert production_planner.progress_metrics(repo2, pid)["completed"] == 1


def test_failed_chunks_are_kept_and_retryable():
    repo, pid = _repo_with_script(make_script(30))
    st = get_settings()
    fake = FakeClient(fail_chunks=1)
    out = pipeline.analyse(repo, pid, fake, st)
    assert out["chunks"]["failed"] == 1 and out["assembled"] is None
    rows = repo.list_chunks(pid)
    assert sum(r["status"] == "DONE" for r in rows) == len(rows) - 1               # partial results preserved
    out2 = pipeline.analyse(repo, pid, fake, st, fresh=False)                       # retry only the failed chunk
    assert out2["assembled"]["scenes"] == 30


def test_user_edits_persist_and_rebuild_keeps_them():
    repo, pid = _repo_with_script(make_script(10))
    pipeline.analyse(repo, pid, FakeClient(), get_settings())
    recs = repo.list_scenes(pid)
    recs[0]["heading"] = "INT. EDITED PLACE - DAY"
    recs[0]["location"] = "EDITED PLACE"
    recs.pop()                                                                       # delete one
    recs.append({"id": None, "scene_number": "99", "heading": "EXT. NEW - DAY", "location": "NEW", "int_ext": "EXT",
                 "time_of_day": "DAY", "characters": ["ANNA"], "has_dialogue": False})
    repo.sync_scenes(pid, recs)
    sc = repo.list_scenes(pid)
    assert len(sc) == 10 and sc[0]["heading"] == "INT. EDITED PLACE - DAY" and sc[-1]["scene_number"] == "99"
    cs = repo.list_characters(pid)
    anna = next(c for c in cs if c["name"].upper() == "ANNA")
    anna["description"] = "Edited by user"
    repo.sync_characters(pid, cs)
    production_planner.rebuild_registers(repo, pid)
    assert next(c for c in repo.list_characters(pid) if c["name"].upper() == "ANNA")["description"] == "Edited by user"
    assert "Edited Place" in {l["name"] for l in repo.list_locations(pid)}
