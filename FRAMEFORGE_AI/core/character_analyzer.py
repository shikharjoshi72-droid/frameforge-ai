"""Character register derived from validated scene data. Counts come from Python, never the LLM."""
from core.utils import norm_character, split_csv, join_csv


def build_characters(scenes: list, char_infos: dict, previous: list | None = None) -> list:
    prev = {norm_character(c["name"]): c for c in (previous or [])}
    total = max(len(scenes), 1)
    acc = {}
    for s in scenes:
        for raw in s["characters"]:
            key = norm_character(raw)
            if not key:
                continue
            a = acc.setdefault(key, {"scenes": [], "costumes": []})
            a["scenes"].append(s)
        for cos in s.get("costumes", []):
            key = norm_character(cos.get("character") or "")
            if key and key in acc:
                acc[key]["costumes"].append(f"Sc {s['scene_number']}: {cos['name']}")
    out, keys = [], list(acc)
    for key, a in acc.items():
        sc = a["scenes"]
        share = len(sc) / total
        role = "Main" if share >= 0.25 else "Supporting" if share >= 0.08 else "Minor"
        info = char_infos.get(key, {})
        old = prev.get(key, {})
        dup = [k for k in keys if k != key and set(key.split()) < set(k.split())]
        notes = old.get("notes") or ""
        if dup and "Possible duplicate" not in notes:
            notes = (notes + f" Possible duplicate of: {', '.join(dup)} - review.").strip()
        out.append({
            "name": key.title() if key.isupper() else key,
            "description": old.get("description") or info.get("description", ""),
            "char_type": old.get("char_type") or info.get("char_type", ""),
            "role": old.get("role") or f"{role} (by scene share)",
            "first_scene": sc[0]["scene_number"], "last_scene": sc[-1]["scene_number"],
            "appearances": len(sc),
            "relationships": old.get("relationships") or join_csv(info.get("relationships", [])),
            "costume_notes": old.get("costume_notes") or "; ".join(dict.fromkeys(a["costumes"])),
            "notes": notes,
        })
    out.sort(key=lambda c: (-c["appearances"], c["name"]))
    return out
