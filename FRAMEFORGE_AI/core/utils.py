"""Small shared helpers."""
import json
import re
from datetime import datetime


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def jload(text, default=None):
    if text is None or text == "":
        return default
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return default


def is_nan(v) -> bool:
    return isinstance(v, float) and v != v


def clean(v):
    """NaN/NaT -> None; numpy scalars -> python."""
    if v is None or is_nan(v):
        return None
    if hasattr(v, "item"):
        try:
            return v.item()
        except Exception:
            pass
    if v.__class__.__name__ in ("NaTType", "NAType"):
        return None
    return v


def split_csv(value) -> list:
    if value is None or is_nan(value):
        return []
    items = list(value) if isinstance(value, (list, tuple)) else re.split(r"[,;\n]", str(value))
    out, seen = [], set()
    for item in items:
        item = str(item).strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            out.append(item)
    return out


def join_csv(items) -> str:
    return ", ".join(str(i) for i in (items or []))


def item_names(items) -> list:
    return [i["name"] if isinstance(i, dict) else str(i) for i in (items or []) if i]


def names_to_items(csv_value, existing_items, default_source="EXPLICIT") -> list:
    """Rebuild resource items from an edited comma list, keeping metadata of unchanged names."""
    existing = {(i.get("name") or "").lower(): i for i in (existing_items or []) if isinstance(i, dict)}
    out = []
    for name in split_csv(csv_value):
        out.append(existing.get(name.lower()) or
                   {"name": name, "source_type": default_source, "description": "",
                    "quantity": None, "character": "", "notes": "added/edited by user"})
    return out


_EXT_RE = re.compile(r"\((?:V\.?O\.?|O\.?S\.?|O\.?C\.?|CONT'?D\.?|CONT\.?|ON PHONE|FILTERED|PRELAP)\)", re.I)


def norm_character(name: str) -> str:
    name = _EXT_RE.sub("", name or "")
    name = re.sub(r"\([^)]*\)", "", name)
    name = re.sub(r"\s+", " ", name).strip(" .:-\t")
    return name.upper()


def pages_label(start, end) -> str:
    if start is None:
        return ""
    return str(start) if end in (None, start) else f"{start}-{end}"
