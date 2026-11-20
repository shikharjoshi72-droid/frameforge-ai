"""Single context-aware assistant grounded in the selected project's saved data."""
from ai import prompts
from core import production_planner


def build_context(repo, pid, max_chars=24000) -> str:
    p = repo.get_project(pid)
    scenes = repo.list_scenes(pid)
    chars = repo.list_characters(pid)
    locs = repo.list_locations(pid)
    days = repo.list_shooting_days(pid)
    ana = repo.get_analysis(pid)
    lines = [f"PROJECT: {p['title']} | genre: {p.get('genre') or 'n/a'} | director: {p.get('director') or 'n/a'} | "
             f"schedule approved: {bool(p.get('schedule_approved'))}",
             f"COUNTS: scenes={len(scenes)}, characters={len(chars)}, locations={len(locs)}, shooting days={len(days)}",
             f"SYNOPSIS: {ana.get('synopsis') or 'not generated'}", "SCENES (number | heading | status | cast | "
             "complexity | summary):"]
    for s in scenes:
        lines.append(f"{s['scene_number']} | {s['heading']} | {s['status']} | {', '.join(s['characters'])} | "
                     f"{s['complexity']} | {(s['description'] or '')[:160]}")
    lines.append("CHARACTERS: " + "; ".join(f"{c['name']} ({c['appearances']} scenes, first sc {c['first_scene']})" for c in chars))
    lines.append("LOCATIONS: " + "; ".join(f"{l['name']} [{l['int_ext']}, {l['day_night']}] scenes {l['scene_numbers']}" for l in locs))
    for cat in ("Equipment", "Prop", "Costume", "Vehicle", "Special Effect"):
        rs = repo.list_resources(pid, cat)
        lines.append(f"{cat.upper()}: " + "; ".join(f"{r['name']} [{r['source_type']}] scenes {r['scene_uids']}" for r in rs))
    for d in days:
        lines.append(f"DAY {d['day_number']} ({d['call_type']}, {d['shoot_date'] or 'date pending'}): "
                     f"{d['location_names']} scenes {', '.join(str(s['scene_number']) for s in d['scenes'])}")
    lines.append("MISSING INFORMATION: " + " | ".join(production_planner.pending_information(repo, pid)))
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[:max_chars] + "\n[context truncated]"


def ask(client, repo, pid, question: str, history: list | None = None) -> str:
    msgs = [{"role": "system", "content": prompts.ASSISTANT_SYSTEM + "\n\nPROJECT DATA:\n" + build_context(repo, pid)}]
    for h in (history or [])[-6:]:
        msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": question})
    return client.chat(msgs, temperature=0.2, max_tokens=900)
