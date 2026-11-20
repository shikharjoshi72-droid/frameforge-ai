"""Deterministic, explainable shooting-schedule engine (+ optional LLM suggestions) and call sheets."""
import re
from datetime import date, timedelta

from ai import prompts
from core.chunking_engine import _TIME_MAP  # noqa: F401  (kept for parity of time vocabulary)
from core.location_analyzer import main_location
from core.utils import item_names, norm_character

TOD_RANK = {"DAWN": 0, "MORNING": 1, "DAY": 2, "CONTINUOUS": 2, "UNKNOWN": 2, "AFTERNOON": 3, "EVENING": 4,
            "DUSK": 5, "NIGHT": 6}
BASE_MIN = {"Low": 45, "Medium": 90, "High": 180}


def estimate_minutes(scene: dict) -> int:
    mins = BASE_MIN.get(scene.get("complexity"), 90)
    mins += 10 * max(0, len(scene.get("characters", [])) - 3)
    mins += 20 * bool(scene.get("vehicles")) + 30 * bool(scene.get("special_effects"))
    return mins


def _category(scene) -> str:
    return "NIGHT" if scene.get("time_of_day") == "NIGHT" else "DAY"


def parse_availability(text: str) -> dict:
    """'ANNA: 2026-12-03, day 4' per line -> {'ANNA': {'2026-12-03', 'day 4'}}"""
    out = {}
    for line in (text or "").splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        vals = {v.strip().lower() for v in re.split(r"[,;]", rest) if v.strip()}
        if norm_character(name) and vals:
            out[norm_character(name)] = vals
    return out


def _dates(n, start, skip_weekends):
    if not start:
        return [None] * n
    d = start if isinstance(start, date) else date.fromisoformat(str(start))
    res = []
    while len(res) < n:
        if not (skip_weekends and d.weekday() >= 5):
            res.append(d.isoformat())
        d += timedelta(days=1)
    return res


def generate_schedule(scenes, start_date=None, capacity=600, max_locations=2, move_minutes=60,
                      skip_weekends=True, availability=None) -> dict:
    """Same input always yields the same output. Everything produced is a PROPOSAL."""
    ordered = sorted(scenes, key=lambda s: (s["seq"], s["id"]))
    groups, order = {}, []
    for s in ordered:
        key = (_category(s), main_location(s["location"]) or "UNKNOWN LOCATION")
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(s)
    # DAY work first, then NIGHT work; inside each, locations by first story appearance
    order.sort(key=lambda k: (k[0] == "NIGHT", min(x["seq"] for x in groups[k])))
    days, cur = [], None

    def new_day(cat):
        d = {"call_type": cat, "scenes": [], "minutes": [], "locations": []}
        days.append(d)
        return d

    for key in order:
        cat, loc = key
        sc = sorted(groups[key], key=lambda s: (TOD_RANK.get(s["time_of_day"], 2), s["int_ext"] != "EXT", s["seq"]))
        if cur is None or cur["call_type"] != cat or len(cur["locations"]) >= max_locations or \
                sum(cur["minutes"]) + move_minutes + estimate_minutes(sc[0]) > capacity:
            cur = new_day(cat)
        cur["locations"].append(loc)
        moved = len(cur["locations"]) > 1
        for s in sc:
            m = estimate_minutes(s)
            if cur["scenes"] and sum(cur["minutes"]) + m + (move_minutes if moved and loc not in cur["locations"][:-1] else 0) > capacity \
                    and cur["scenes"]:
                cur = new_day(cat)
                cur["locations"].append(loc)
                moved = False
            cur["scenes"].append(s)
            cur["minutes"].append(m)
    dates = _dates(len(days), start_date, skip_weekends)
    availability = availability or {}
    out_days, conflicts, appear = [], [], {}
    for i, d in enumerate(days):
        n = i + 1
        cast = sorted({norm_character(c) for s in d["scenes"] for c in s["characters"]})
        total = sum(d["minutes"]) + move_minutes * max(0, len(d["locations"]) - 1)
        for c in cast:
            appear.setdefault(c, []).append(n)
            blocked = availability.get(c, set())
            if f"day {n}" in blocked or str(n) in blocked or (dates[i] and dates[i] in blocked):
                conflicts.append({"type": "availability", "day": n,
                                  "message": f"{c} is marked unavailable for Day {n}"
                                             f"{' (' + dates[i] + ')' if dates[i] else ''} but is required."})
        expl = (f"Day {n} ({d['call_type'].lower()} unit): {', '.join(l.title() for l in d['locations'])}; "
                f"{len(d['scenes'])} scene(s), est. {total}/{capacity} min incl. "
                f"{move_minutes * max(0, len(d['locations']) - 1)} min company move. Grouped by location, then time "
                f"of day; story order kept within each location.")
        out_days.append({"day_number": n, "shoot_date": dates[i], "call_type": d["call_type"], "est_minutes": total,
                         "location_names": ", ".join(l.title() for l in d["locations"]), "explanation": expl,
                         "scene_ids": [s["id"] for s in d["scenes"]], "scene_minutes": d["minutes"], "cast": cast})
    for c, nums in appear.items():
        if len(nums) > 1 and nums[-1] - nums[0] + 1 > len(nums) + 2:
            conflicts.append({"type": "split-availability", "day": nums[0],
                              "message": f"{c} is needed on non-consecutive days {nums} - confirm availability."})
    loc_days = {}
    for d in out_days:
        for l in d["location_names"].split(", "):
            loc_days.setdefault(l, []).append(d["day_number"])
    for l, nums in loc_days.items():
        if len(nums) > 1 and nums[-1] - nums[0] + 1 > len(nums):
            conflicts.append({"type": "location-split", "day": nums[0],
                              "message": f"Location {l} is revisited on days {nums} (capacity or day/night split)."})
    stats = {"days": len(out_days), "scenes": sum(len(d["scene_ids"]) for d in out_days),
             "company_moves": sum(max(0, len(d["location_names"].split(", ")) - 1) for d in out_days)}
    return {"days": out_days, "conflicts": conflicts, "stats": stats, "params": {
        "capacity": capacity, "max_locations": max_locations, "move_minutes": move_minutes}}


def schedule_summary_text(days, scenes_by_id) -> str:
    lines = []
    for d in days:
        nums = [str(scenes_by_id[i]["scene_number"]) for i in d["scene_ids"] if i in scenes_by_id]
        lines.append(f"Day {d['day_number']} [{d['call_type']}] {d['location_names']}: scenes {', '.join(nums)} "
                     f"(~{d['est_minutes']} min)")
    return "\n".join(lines)


def ai_suggestions(client, days, scenes, conflicts) -> str:
    by_id = {s["id"]: s for s in scenes}
    text = schedule_summary_text(days, by_id)
    if conflicts:
        text += "\nConflicts:\n" + "\n".join(f"- {c['message']}" for c in conflicts)
    return client.chat(prompts.schedule_suggestion_prompt(text), max_tokens=900)


def build_call_sheet(project: dict, day: dict, overrides: dict | None = None) -> dict:
    ov = overrides or {}
    P = "PENDING"
    scenes = day["scenes"]
    cast = sorted({norm_character(c) for s in scenes for c in s["characters"]})
    uniq = lambda xs: list(dict.fromkeys(xs))
    costumes = uniq(f"{c['name']}" + (f" ({c['character']})" if c.get("character") else "")
                    for s in scenes for c in s["costumes"])
    special = []
    for s in scenes:
        if s["time_of_day"] == "NIGHT":
            special.append(f"Sc {s['scene_number']}: night shoot")
        for k, label in (("vehicles", "vehicle"), ("special_effects", "effect")):
            for n in item_names(s[k]):
                special.append(f"Sc {s['scene_number']}: {label} - {n}")
    if ov.get("instructions"):
        special.append(ov["instructions"])
    return {
        "production": project["title"], "day_number": day["day_number"],
        "date": day.get("shoot_date") or P, "call_time": ov.get("call_time") or P,
        "wrap_time": ov.get("wrap_time") or P, "location": day.get("location_names") or P,
        "call_type": day.get("call_type"), "est_minutes": day.get("est_minutes"),
        "scenes": [{"number": s["scene_number"], "heading": s["heading"], "pages": s["page_ref"],
                    "cast": ", ".join(s["characters"])} for s in scenes],
        "cast": cast, "crew": ov.get("crew") or P,
        "props": uniq(n for s in scenes for n in item_names(s["props"])),
        "equipment": uniq(n for s in scenes for n in item_names(s["equipment"])),
        "costumes": costumes, "special": special,
        "emergency_contact": ov.get("emergency_contact") or P,
        "status": "PROPOSED" if not project.get("schedule_approved") else "APPROVED",
    }
