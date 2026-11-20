"""Per-chunk LLM extraction, validation against the source text, and merge into scene records."""
import re

from ai import prompts
from config.constants import COMPLEXITY, GENERIC_EQUIPMENT, INT_EXT, TIMES_OF_DAY
from core.chunking_engine import extract_speakers
from core.utils import norm_character, pages_label


def extract_chunk(client, payload: dict) -> dict:
    try:
        from ai.schemas import ChunkResult
    except ImportError:  # pydantic missing; real client would fail with a clear error
        ChunkResult = None
    return client.chat_json(prompts.chunk_prompt(payload), ChunkResult)


def estimate_complexity(scene: dict) -> str:
    score = len(scene.get("characters", [])) / 4 + len(scene.get("vehicles", [])) + 2 * len(scene.get("special_effects", []))
    score += 1 if scene.get("time_of_day") == "NIGHT" else 0
    return "High" if score >= 4 else "Medium" if score >= 2 else "Low"


def _in_text(name: str, text: str) -> bool:
    n = norm_character(name)
    return bool(n) and n in text.upper()


def _clean_items(items, filter_generic=False):
    out, seen = [], set()
    for it in items or []:
        name = (it.get("name") or "").strip()
        key = name.lower()
        if not name or key in seen or (filter_generic and key in GENERIC_EQUIPMENT):
            continue
        seen.add(key)
        out.append({k: it.get(k) for k in ("name", "source_type", "description", "quantity", "character", "notes")})
    return out


def build_scene(block_meta: dict, raw_text: str, ai: dict | None, idx: int) -> dict:
    """Combine Python-parsed heading facts with validated AI output for one scene block."""
    from core.chunking_engine import parse_heading
    parsed = parse_heading(block_meta["heading"]) if block_meta.get("heading_ok") or block_meta["heading"].upper().startswith(("INT", "EXT", "I/E", "SCENE")) else {}
    reasons = [block_meta["flag"]] if block_meta.get("flag") else []
    ai = ai or {}
    if not ai:
        reasons.append("The model returned no data for this scene block; only heading facts are filled in.")

    int_ext = parsed.get("int_ext") if parsed.get("int_ext") in INT_EXT and parsed.get("int_ext") != "UNKNOWN" else ""
    location = parsed.get("location", "")
    tod = parsed.get("time_of_day", "") if parsed.get("time_of_day") != "UNKNOWN" else ""
    if not int_ext and ai.get("int_ext", "").upper() in INT_EXT:
        int_ext = ai["int_ext"].upper()
        reasons.append("INT/EXT inferred by AI (heading unclear).")
    if not location and ai.get("location"):
        location = ai["location"].strip().upper()
        reasons.append("Location inferred by AI (heading unclear).")
    if not tod and ai.get("time_of_day", "").upper() in TIMES_OF_DAY:
        tod = ai["time_of_day"].upper()
    if tod == "CONTINUOUS":
        reasons.append("Time of day is relative ('later'/'continuous'); confirm actual day/night.")

    # ---- characters: validate against source text + deterministic speaker cues ----
    speakers = extract_speakers(raw_text)
    present, dropped = [], []
    for n in ai.get("characters_present", []):
        (present if _in_text(n, raw_text) else dropped).append(n)
    voice = [n for n in ai.get("characters_voice_only", []) if _in_text(n, raw_text)]
    mentioned = [n for n in ai.get("characters_mentioned", []) if _in_text(n, raw_text)]
    known = {norm_character(n) for n in present + voice}
    added = []
    for name, kind in speakers.items():
        if norm_character(name) in known:
            continue
        if kind == "voice":
            voice.append(name)
        else:
            present.append(name)
            added.append(name)
        known.add(norm_character(name))
    if dropped:
        reasons.append(f"Removed AI characters not found in the scene text: {', '.join(dropped)}.")
    if added:
        reasons.append(f"Added speaking characters detected from dialogue cues: {', '.join(added)}.")
    mentioned += [f"{n} (voice only)" for n in voice]
    mentioned = [m for m in dict.fromkeys(mentioned) if norm_character(m.replace("(voice only)", "")) not in
                 {norm_character(p) for p in present}]

    scene = {
        "scene_uid": f"S{idx:03d}", "seq": float(idx), "scene_number": block_meta["scene_number"],
        "heading": block_meta["heading"], "page_ref": pages_label(block_meta["page_start"], block_meta["page_end"]),
        "location": location, "int_ext": int_ext or "UNKNOWN", "time_of_day": tod or "UNKNOWN",
        "description": ai.get("description", ""), "main_action": ai.get("main_action", ""),
        "has_dialogue": bool(ai.get("has_dialogue")) or bool(speakers),
        "characters": list(dict.fromkeys(present)), "mentioned": mentioned,
        "props": _clean_items(ai.get("props")), "costumes": _clean_items(ai.get("costumes")),
        "vehicles": _clean_items(ai.get("vehicles")), "special_effects": _clean_items(ai.get("special_effects")),
        "equipment": _clean_items(ai.get("equipment"), filter_generic=True),
        "confidence": float(ai.get("confidence", 0.0)) if ai else 0.0,
        "evidence": (ai.get("evidence") or "")[:300], "raw_text": raw_text, "source": "AI",
    }
    comp = ai.get("complexity", "").capitalize()
    scene["complexity"] = comp if comp in COMPLEXITY else estimate_complexity(scene)
    if ai.get("needs_review") and ai.get("review_reason"):
        reasons.append(ai["review_reason"])
    scene["needs_review"] = int(bool(reasons) and (bool(ai.get("needs_review")) or not ai or bool(dropped)
                                                   or bool(block_meta.get("flag")) or not int_ext or not location
                                                   or tod == "CONTINUOUS"))
    scene["review_reason"] = " | ".join(dict.fromkeys(r for r in reasons if r))
    return scene


def merge_chunks(chunk_rows: list):
    """chunk_rows: repository rows (payload + result). Returns (scenes, char_infos, summaries)."""
    order, meta, texts, ai_by_block = [], {}, {}, {}
    char_infos, summaries = {}, []
    for row in sorted(chunk_rows, key=lambda r: r["idx"]):
        res = row["result"] or {}
        if res.get("chunk_summary"):
            summaries.append(res["chunk_summary"])
        for u in row["payload"]["units"]:
            bid = u["block_id"]
            if bid not in meta:
                order.append(bid)
                meta[bid] = u
            texts.setdefault(bid, []).append(u["text"])
        for s in res.get("scenes", []):
            prev = ai_by_block.get(s["block_id"])
            if prev is None:
                ai_by_block[s["block_id"]] = s
            else:  # long scene split over chunks: union lists, keep first text fields
                for k in ("characters_present", "characters_voice_only", "characters_mentioned"):
                    prev[k] = list(dict.fromkeys(prev[k] + s[k]))
                for k in ("props", "costumes", "vehicles", "special_effects", "equipment"):
                    prev[k] = prev[k] + s[k]
                prev["description"] = (prev["description"] + " " + s["description"]).strip()
                prev["has_dialogue"] = prev["has_dialogue"] or s["has_dialogue"]
        for c in res.get("characters", []):
            key = norm_character(c["name"])
            if not key:
                continue
            cur = char_infos.setdefault(key, {"name": key, "description": "", "char_type": "", "relationships": []})
            cur["description"] = cur["description"] or c.get("description", "")
            cur["char_type"] = cur["char_type"] or c.get("char_type", "")
            cur["relationships"] = list(dict.fromkeys(cur["relationships"] + c.get("relationships", [])))
    scenes = [build_scene(meta[b], "\n\n".join(texts[b]), ai_by_block.get(b), i) for i, b in enumerate(order, 1)]
    return scenes, char_infos, summaries


def reanalyze_scene(client, scene: dict, known_characters: list) -> dict:
    """Re-run the LLM on one stored scene and return updated field values (not yet saved)."""
    try:
        from ai.schemas import SceneRedo
    except ImportError:
        SceneRedo = None
    res = client.chat_json(prompts.scene_redo_prompt(scene["heading"], scene.get("raw_text") or "", known_characters),
                           SceneRedo)["scene"]
    meta = {"heading": scene["heading"], "heading_ok": True, "flag": "", "scene_number": scene["scene_number"],
            "page_start": None, "page_end": None}
    new = build_scene(meta, scene.get("raw_text") or "", res, 0)
    keep = {k: new[k] for k in ("description", "main_action", "has_dialogue", "characters", "mentioned", "props",
                                "costumes", "vehicles", "special_effects", "equipment", "complexity",
                                "confidence", "evidence", "needs_review", "review_reason")}
    return keep
