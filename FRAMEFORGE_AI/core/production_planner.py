"""Rebuild derived registers from scenes; compute pending information and progress metrics."""
from core import character_analyzer, location_analyzer, resource_analyzer
from core.utils import split_csv


def rebuild_registers(repo, pid):
    scenes = repo.list_scenes(pid)
    char_infos = repo.get_analysis(pid).get("char_infos", {})
    repo.sync_characters(pid, _with_ids(character_analyzer.build_characters(scenes, char_infos, repo.list_characters(pid)),
                                        repo.list_characters(pid), "name"))
    repo.link_scene_characters(pid)
    repo.sync_locations(pid, _with_ids(location_analyzer.build_locations(scenes, repo.list_locations(pid)),
                                       repo.list_locations(pid), "name"))
    manual = [r for r in repo.list_resources(pid) if r["manual"]]
    derived = resource_analyzer.build_resources(scenes)
    manual_keys = {(r["category"], r["name"].lower()) for r in manual}
    derived = [d for d in derived if (d["category"], d["name"].lower()) not in manual_keys]
    existing = {(r["category"], r["name"].lower()): r["id"] for r in repo.list_resources(pid) if not r["manual"]}
    for d in derived:
        d["id"] = existing.get((d["category"], d["name"].lower()))
    repo.sync_resources(pid, manual + derived)


def _with_ids(new_rows, old_rows, key):
    ids = {r[key].lower(): r["id"] for r in old_rows}
    for r in new_rows:
        r["id"] = ids.get(r[key].lower())
    return new_rows


def pending_information(repo, pid) -> list:
    p = repo.get_project(pid)
    scenes = repo.list_scenes(pid)
    items = []
    if not scenes:
        return ["No scenes extracted yet - upload and analyse a screenplay."]
    if not p.get("director"):
        items.append("Director name not provided.")
    if not p.get("company"):
        items.append("Production company not provided.")
    if not p.get("start_date"):
        items.append("Production start date not set - shooting dates are 'Pending'.")
    flagged = [s for s in scenes if s["needs_review"]]
    if flagged:
        items.append(f"{len(flagged)} scene(s) flagged for review: " + ", ".join(str(s["scene_number"]) for s in flagged[:15]))
    unk = [s for s in scenes if s["time_of_day"] in ("UNKNOWN", "CONTINUOUS")]
    if unk:
        items.append(f"{len(unk)} scene(s) have unknown/relative day-night information.")
    nodesc = [c for c in repo.list_characters(pid) if not (c["description"] or "").strip()]
    if nodesc:
        items.append(f"{len(nodesc)} character(s) have no description.")
    days = repo.list_shooting_days(pid)
    if not days:
        items.append("No shooting schedule generated yet.")
    elif not p.get("schedule_approved"):
        items.append("Shooting schedule is a PROPOSAL and has not been approved.")
    else:
        sched = {s["id"] for d in days for s in d["scenes"]}
        missing = [s for s in scenes if s["id"] not in sched]
        if missing:
            items.append(f"{len(missing)} scene(s) are not assigned to any shooting day.")
    for d in days:
        cs = repo.get_call_sheet(d["id"])
        if not cs.get("call_time") or not cs.get("emergency_contact"):
            items.append("Call sheets are missing reporting time and/or emergency contact (see Call Sheets).")
            break
    if not repo.get_analysis(pid).get("synopsis"):
        items.append("Story analysis has not been generated.")
    return items


def progress_metrics(repo, pid) -> dict:
    scenes = repo.list_scenes(pid)
    counts = repo.status_counts(pid)
    total = len(scenes)
    done = counts.get("Completed", 0)
    days = repo.list_shooting_days(pid)
    done_locs = {s["location"] for s in scenes if s["status"] == "Completed"}
    return {"total": total, "completed": done, "pending": total - done,
            "pct": round(100 * done / total, 1) if total else 0.0, "counts": counts,
            "days_planned": len(days), "days_completed": sum(1 for d in days if d["completed"]),
            "locations_covered": len(done_locs),
            "open_requirements": sum(1 for r in repo.list_resources(pid) if r["source_type"] != "RECOMMENDED"
                                     and any(s["status"] != "Completed" and s["scene_number"] in split_csv(r["scene_uids"])
                                             for s in scenes))}
