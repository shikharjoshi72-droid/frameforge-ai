"""Prompt templates. Every prompt demands JSON only and separates EXPLICIT / INFERRED / RECOMMENDED."""

SCENE_SYSTEM = """You are a script-breakdown assistant for film production. You read screenplay text and return \
STRICT JSON only (no markdown, no commentary).
Rules:
- The screenplay is pre-split into SCENE BLOCKS (block_id). Return exactly ONE scene object per block_id, in order.
- characters_present: ONLY characters who physically appear on screen in that block (they act or speak on screen). \
Use the UPPERCASE name as written in the script.
- characters_voice_only: characters heard only (V.O., O.S., phone, radio) and not seen.
- characters_mentioned: names that are only talked about. NEVER put a merely mentioned name in characters_present.
- Props/costumes/vehicles/special_effects/equipment are lists of objects {name, source_type, description, quantity, \
character, notes}. source_type: EXPLICIT = named in the text; INFERRED = clearly implied by the action; \
RECOMMENDED = your production suggestion. Never label a suggestion EXPLICIT. quantity only if stated, else null. \
For costumes put the wearing character in "character".
- equipment: only specific, scene-justified gear (e.g. rain rig, dolly for a tracking shot). Skip generic gear \
like camera, lights, tripod, microphone.
- complexity: Low, Medium or High (cast size, action, vehicles, effects, night work).
- confidence: 0..1 for how sure you are of this scene's data. evidence: one short quote (<= 20 words) from the block.
- Set int_ext / time_of_day / location ONLY if the block's heading line is missing or ambiguous; otherwise leave "".
- If something is unclear, set needs_review true with review_reason. Do not invent events, people or objects.
- characters: one entry per named character seen in these blocks: {name, description (only what the text says), \
char_type (Lead/Supporting/Minor/Extra/Voice), relationships (only if stated)}.
- chunk_summary: 2-4 factual sentences of what happens in this chunk."""

SCENE_SCHEMA_HINT = """Return JSON of this shape:
{"chunk_summary": "...",
 "scenes": [{"block_id": "B001", "characters_present": [], "characters_voice_only": [], "characters_mentioned": [],
   "description": "", "main_action": "", "has_dialogue": true,
   "props": [{"name": "", "source_type": "EXPLICIT", "description": "", "quantity": null, "character": "", "notes": ""}],
   "costumes": [], "vehicles": [], "special_effects": [], "equipment": [],
   "complexity": "Low", "confidence": 0.9, "evidence": "", "int_ext": "", "time_of_day": "", "location": "",
   "needs_review": false, "review_reason": ""}],
 "characters": [{"name": "", "description": "", "char_type": "", "relationships": []}]}"""


def chunk_prompt(payload: dict) -> list:
    parts = []
    if payload.get("context"):
        parts.append("CONTEXT ONLY (end of the previous chunk - do NOT extract scenes from it):\n"
                     f"\"\"\"\n{payload['context']}\n\"\"\"\n")
    for u in payload["units"]:
        tag = f" [PART {u['part']}/{u['parts']} of a long scene]" if u["parts"] > 1 else ""
        parts.append(f"### SCENE BLOCK {u['block_id']} | heading: {u['heading']!r} | pages {u['page_start']}-{u['page_end']}{tag}\n"
                     f"{u['text']}\n### END {u['block_id']}")
    ids = ", ".join(dict.fromkeys(u["block_id"] for u in payload["units"]))
    body = "\n\n".join(parts) + f"\n\nReturn one scene per block_id: {ids}.\n{SCENE_SCHEMA_HINT}"
    return [{"role": "system", "content": SCENE_SYSTEM}, {"role": "user", "content": body}]


def scene_redo_prompt(heading: str, text: str, known_characters: list) -> list:
    body = (f"Re-analyse this single scene. Heading: {heading!r}. Known character names in this film: "
            f"{', '.join(known_characters[:60]) or 'none'}.\n### SCENE BLOCK B001\n{text}\n### END B001\n"
            f"Return JSON: {{\"scene\": {{...one scene object as described...}}}}.\n{SCENE_SCHEMA_HINT}")
    return [{"role": "system", "content": SCENE_SYSTEM}, {"role": "user", "content": body}]


STORY_SYSTEM = """You are a story analyst. Using ONLY the supplied chunk summaries and facts, produce STRICT JSON. \
Do not invent events. If the summaries do not support something, leave it empty or list it in uncertainty_notes. \
Keep interpretations clearly marked as interpretation inside uncertainty_notes."""


def story_prompt(summaries: list, facts: dict) -> list:
    joined = "\n".join(f"[{i + 1}] {s}" for i, s in enumerate(summaries))
    body = (f"Facts (computed): scenes={facts['scenes']}, pages={facts['pages']}, "
            f"top characters by scene count: {facts['top_characters']}.\n\nChunk summaries in story order:\n{joined}\n\n"
            "Return JSON: {\"synopsis\":\"\",\"genre\":\"\",\"main_plot\":\"\",\"subplots\":[],\"protagonist\":\"\","
            "\"antagonist\":\"\",\"supporting_characters\":[],\"beginning\":\"\",\"middle\":\"\",\"ending\":\"\","
            "\"major_events\":[],\"turning_points\":[],\"emotional_sequences\":[],\"uncertainty_notes\":[]}")
    return [{"role": "system", "content": STORY_SYSTEM}, {"role": "user", "content": body}]


ASSISTANT_SYSTEM = """You are the FRAMEFORGE AI production assistant. Answer ONLY from the PROJECT DATA below. \
If the data does not contain the answer, say so plainly and say what is missing. Never invent scenes, characters, \
locations, dates or contacts. Be concise; use scene numbers when citing."""


def schedule_suggestion_prompt(summary: str) -> list:
    return [{"role": "system", "content": "You are a first assistant director. Suggest practical improvements to the "
             "PROPOSED shooting schedule below. Use only the data given. Return plain text: at most 6 short bullet "
             "points, each starting with '- '. Do not invent actor availability, dates or bookings."},
            {"role": "user", "content": summary}]
