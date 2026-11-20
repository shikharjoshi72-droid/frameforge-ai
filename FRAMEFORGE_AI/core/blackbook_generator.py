"""Collect saved project data into a bundle and produce the Black Book PDF."""
from datetime import datetime

from config.constants import SCENE_STATUSES  # noqa: F401
from config.settings import BLACKBOOK_DIR
from core import production_planner
from core.schedule_generator import build_call_sheet
from exports import pdf_generator


class BlackBookError(Exception):
    pass


def collect_bundle(repo, pid) -> dict:
    p = repo.get_project(pid)
    scenes = repo.list_scenes(pid)
    if not scenes:
        raise BlackBookError("No scenes saved yet. Analyse a screenplay before generating a Black Book.")
    days = repo.list_shooting_days(pid)
    for d in days:
        d["call_sheet"] = build_call_sheet(p, d, repo.get_call_sheet(d["id"]))
    return {"project": p, "analysis": repo.get_analysis(pid), "characters": repo.list_characters(pid), "scenes": scenes,
            "locations": repo.list_locations(pid), "resources": repo.list_resources(pid),
            "schedule": {"approved": bool(p.get("schedule_approved")), "days": days},
            "progress": production_planner.progress_metrics(repo, pid),
            "pending": production_planner.pending_information(repo, pid),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "version": (p.get("bb_version") or 0) + 1}


def generate(repo, pid) -> dict:
    """Build the PDF from SAVED data, verify it, record it. Returns {path, bytes, verification, version}."""
    bundle = collect_bundle(repo, pid)
    BLACKBOOK_DIR.mkdir(parents=True, exist_ok=True)
    path = BLACKBOOK_DIR / f"{pid}_BlackBook_v{bundle['version']}.pdf"
    try:
        titles = pdf_generator.build_blackbook(bundle, str(path))
    except Exception as exc:
        raise BlackBookError(f"PDF generation failed: {exc.__class__.__name__}: {exc}") from exc
    verification = pdf_generator.verify_pdf(str(path), titles[1:])
    if not verification["ok"]:
        raise BlackBookError(f"Generated PDF failed verification: {verification}")
    data = path.read_bytes()
    repo.update_project(pid, bb_version=bundle["version"])
    repo.add_document(pid, "blackbook", path.name, "", len(data), verification["pages"], str(path))
    return {"path": str(path), "bytes": data, "verification": verification, "version": bundle["version"]}
