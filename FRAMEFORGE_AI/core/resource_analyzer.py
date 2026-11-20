"""Aggregate per-scene resource items into registers, keeping the most certain source type."""
from config.constants import SOURCE_RANK
from core.utils import join_csv

_CATS = [("props", "Prop"), ("costumes", "Costume"), ("equipment", "Equipment"), ("vehicles", "Vehicle"),
         ("special_effects", "Special Effect")]


def build_resources(scenes: list) -> list:
    agg = {}
    for s in scenes:
        for field, cat in _CATS:
            for it in s.get(field, []):
                name = (it.get("name") or "").strip()
                if not name:
                    continue
                key = (cat, name.lower() + ("|" + it["character"].lower() if cat == "Costume" and it.get("character") else ""))
                a = agg.setdefault(key, {"name": name, "category": cat, "scenes": [], "src": it.get("source_type") or "INFERRED",
                                         "desc": it.get("description") or "", "qty": None, "notes": []})
                a["scenes"].append(str(s["scene_number"]))
                if SOURCE_RANK.get(it.get("source_type"), 1) < SOURCE_RANK.get(a["src"], 1):
                    a["src"] = it["source_type"]
                a["desc"] = a["desc"] or (it.get("description") or "")
                a["qty"] = a["qty"] or it.get("quantity")
                if it.get("character"):
                    a["notes"].append(f"Character: {it['character']}")
                if it.get("notes") and it["notes"] != "added/edited by user":
                    a["notes"].append(it["notes"])
    rows = []
    for (cat, _), a in agg.items():
        rows.append({"name": a["name"], "category": cat, "scene_uids": join_csv(dict.fromkeys(a["scenes"])),
                     "source_type": a["src"], "description": a["desc"], "quantity": a["qty"],
                     "notes": "; ".join(dict.fromkeys(a["notes"])), "manual": 0})
    return sorted(rows, key=lambda r: (r["category"], r["name"].lower()))
