"""Location register. Locations merge only on exact normalised names; look-alikes are flagged, not merged."""
import re
from difflib import SequenceMatcher

from core.utils import item_names, join_csv

_SYN = [{"COFFEE SHOP", "CAFE", "COFFEEHOUSE", "COFFEE HOUSE"}, {"APARTMENT", "FLAT"}, {"CAR", "VEHICLE"},
        {"POLICE STATION", "PRECINCT"}, {"HOSPITAL", "CLINIC"}]


def main_location(loc: str) -> str:
    base = re.split(r"\s+-\s+|\s+/\s+", (loc or "").strip())[0]
    base = re.sub(r"^(THE|A|AN)\s+", "", re.sub(r"[^\w\s']", " ", base.upper()))
    return re.sub(r"\s+", " ", base).strip()


def _similar(a: str, b: str) -> bool:
    if a == b:
        return False
    if any(a in g and b in g for g in _SYN):
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.82 or (len(a) > 3 and (a in b.split() or b in a.split()))


def build_locations(scenes: list, previous: list | None = None) -> list:
    prev = {main_location(p["name"]): p for p in (previous or [])}
    groups = {}
    for s in scenes:
        key = main_location(s["location"])
        if key:
            groups.setdefault(key, []).append(s)
    keys = list(groups)
    out = []
    for key, sc in groups.items():
        ie = {s["int_ext"] for s in sc if s["int_ext"] != "UNKNOWN"}
        tod = sorted({s["time_of_day"] for s in sc if s["time_of_day"] != "UNKNOWN"})
        props = sorted({n for s in sc for n in item_names(s["props"])})
        subs = sorted({s["location"] for s in sc if s["location"].upper() != key and key in s["location"].upper()})
        score = len(sc) + (2 if "NIGHT" in tod else 0) + sum(1 for s in sc if s["special_effects"] or s["vehicles"])
        comp = "High" if score >= 8 else "Medium" if score >= 4 else "Low"
        similar = [k for k in keys if _similar(key, k)]
        old = prev.get(key, {})
        out.append({
            "name": key.title(),
            "description": old.get("description") or (f"Sub-areas: {', '.join(subs)}" if subs else ""),
            "int_ext": "/".join(sorted(ie)) if ie else "UNKNOWN",
            "day_night": ", ".join(tod) or "UNKNOWN",
            "scene_numbers": join_csv([s["scene_number"] for s in sc]),
            "props": join_csv(props), "complexity": old.get("complexity") or comp,
            "notes": old.get("notes", ""),
            "duplicate_hint": f"Possibly the same as: {', '.join(k.title() for k in similar)}" if similar else "",
        })
    return sorted(out, key=lambda l: l["name"])
