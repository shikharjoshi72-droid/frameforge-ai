"""Screenplay-aware segmentation and chunking.

Python (not the LLM) decides scene boundaries from headings. The LLM then fills in one record
per SCENE BLOCK, so scene count, order and numbering are deterministic.
"""
import re
from dataclasses import dataclass, field

_PREFIX = (r"(?:INT\.?\s*/\s*EXT\.?|EXT\.?\s*/\s*INT\.?|I\s*/\s*E\.?|INT\.?|EXT\.?|INTERIOR|EXTERIOR)")
_H_UP = re.compile(
    rf"^\s*(?:(?P<n1>\d+[A-Z]{{0,2}})[\.\)]?\s+)?(?P<p>{_PREFIX})(?=[\s\.\-\u2013\u2014])[\.\s\-\u2013\u2014]*"
    rf"(?P<rest>\S.*?)\s*(?:\s(?P<n2>\d+[A-Z]{{0,2}}))?\s*$")
_INF_PREFIX = r"(?:int\.?\s*/\s*ext\.|ext\.?\s*/\s*int\.|i/e\.|int\.|ext\.)"
_H_INF = re.compile(
    rf"^\s*(?:(?P<n1>\d+[A-Z]{{0,2}})[\.\)]?\s+)?(?P<p>{_INF_PREFIX})\s*(?P<rest>\S.*?)\s*(?:\s(?P<n2>\d+[A-Z]{{0,2}}))?\s*$",
    re.I)
_H_SCENE = re.compile(r"^\s*SCENE\s+(?P<n1>\d+[A-Z]?)\s*[:\.\-\u2013]?\s*(?P<rest>.*)$", re.I)

_TIME_MAP = {"DAY": "DAY", "NIGHT": "NIGHT", "DAWN": "DAWN", "SUNRISE": "DAWN", "DUSK": "DUSK",
             "SUNSET": "DUSK", "MORNING": "MORNING", "AFTERNOON": "AFTERNOON", "EVENING": "EVENING",
             "LATER": "CONTINUOUS", "CONTINUOUS": "CONTINUOUS", "SAME": "CONTINUOUS",
             "MOMENTS LATER": "CONTINUOUS", "SAME TIME": "CONTINUOUS", "NOON": "DAY", "MIDNIGHT": "NIGHT",
             "DAYTIME": "DAY", "NIGHTTIME": "NIGHT"}


def match_heading(line: str):
    s = line.strip()
    if not s or len(s) > 120:
        return None
    m = _H_UP.match(s)
    kind = "standard"
    if not m:
        m = _H_INF.match(s)
    if not m:
        m = _H_SCENE.match(s)
        kind = "scene_word"
    if not m:
        return None
    return m, kind


def parse_heading(line: str) -> dict:
    res = match_heading(line)
    info = {"scene_no": None, "int_ext": "UNKNOWN", "location": "", "time_of_day": "UNKNOWN", "ok": False}
    if not res:
        return info
    m, kind = res
    gd = m.groupdict()
    info["scene_no"] = gd.get("n1") or gd.get("n2")
    if kind == "scene_word":
        info["location"] = (gd.get("rest") or "").strip()
        return info
    p = re.sub(r"[\.\s]", "", gd["p"].upper())
    info["int_ext"] = ("INT/EXT" if "/" in p or p in ("IE",) else
                       "INT" if p.startswith("INT") else "EXT")
    rest = re.sub(r"\s+", " ", gd["rest"]).strip()
    parts = [x.strip() for x in re.split(r"\s+[-\u2013\u2014]\s+|\s*[\u2013\u2014]\s*", rest) if x.strip()]
    if len(parts) > 1 and parts[-1].upper().strip(".") in _TIME_MAP:
        info["time_of_day"] = _TIME_MAP[parts[-1].upper().strip(".")]
        parts = parts[:-1]
    else:
        m2 = re.search(r"\(([A-Za-z ]+)\)\s*$", rest)
        if m2 and m2.group(1).upper() in _TIME_MAP:
            info["time_of_day"] = _TIME_MAP[m2.group(1).upper()]
            parts = [re.sub(r"\([A-Za-z ]+\)\s*$", "", rest).strip()]
    info["location"] = " - ".join(parts).strip(" -")
    info["ok"] = bool(info["location"])
    return info


@dataclass
class SceneBlock:
    block_id: str
    index: int
    heading: str
    scene_number: str
    page_start: int
    page_end: int
    text: str
    heading_ok: bool
    parsed: dict
    flag: str = ""


@dataclass
class Chunk:
    chunk_id: str
    index: int
    units: list
    context: str
    page_start: int
    page_end: int

    def to_payload(self) -> dict:
        return {"chunk_id": self.chunk_id, "index": self.index, "units": self.units, "context": self.context,
                "page_start": self.page_start, "page_end": self.page_end}


def segment(pages: list, title_page_limit: int = 1500):
    """Split pages into scene blocks. Returns (blocks, info)."""
    lines = []  # (line, page_no)
    for pno, ptxt in enumerate(pages, start=1):
        for ln in ptxt.split("\n"):
            lines.append((ln, pno))
    starts = [i for i, (ln, _) in enumerate(lines) if match_heading(ln)]
    info = {"headings_found": len(starts), "skipped_front_matter_chars": 0, "mode": "headings"}
    blocks = []

    def make(idx, chunk_lines, heading, parsed, ok, flag):
        text = "\n".join(ln for ln, _ in chunk_lines).strip("\n")
        pnos = [p for _, p in chunk_lines] or [1]
        num = parsed.get("scene_no") or str(idx)
        return SceneBlock(f"B{idx:03d}", idx, heading, str(num), min(pnos), max(pnos), text, ok, parsed, flag)

    if not starts:
        info["mode"] = "no_headings"
        body = [(ln, p) for ln, p in lines]
        step = 60
        for n, i in enumerate(range(0, len(body), step), start=1):
            seg = body[i:i + step]
            if not "".join(l for l, _ in seg).strip():
                continue
            blocks.append(make(len(blocks) + 1, seg, f"UNHEADED SEGMENT {n}", {"scene_no": None}, False,
                               "No scene headings detected in the screenplay; segment boundary is arbitrary."))
        return blocks, info

    pre = lines[:starts[0]]
    pre_text = "\n".join(l for l, _ in pre).strip()
    if pre_text:
        if len(pre_text) <= title_page_limit and (pre[-1][1] if pre else 1) <= 2:
            info["skipped_front_matter_chars"] = len(pre_text)
        else:
            blocks.append(make(1, pre, "UNHEADED OPENING (before first scene heading)", {"scene_no": None}, False,
                               "Text before the first scene heading; may be an unheaded scene or front matter."))
    for n, s in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        seg = lines[s:end]
        heading = seg[0][0].strip()
        parsed = parse_heading(heading)
        flag = ""
        if parsed["int_ext"] == "UNKNOWN" or not parsed["ok"]:
            flag = "Heading is missing INT/EXT or a location; verify scene details."
        blocks.append(make(len(blocks) + 1, seg, heading, parsed, parsed["ok"], flag))
    return blocks, info


def _split_long(text: str, max_chars: int) -> list:
    if len(text) <= max_chars:
        return [text]
    paras, parts, cur = re.split(r"\n\s*\n", text), [], ""
    for para in paras:
        while len(para) > max_chars:  # a single enormous paragraph
            cut = para.rfind("\n", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(para[:cut])
            para = para[cut:].lstrip("\n")
        if cur and len(cur) + len(para) + 2 > max_chars:
            parts.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        parts.append(cur)
    return parts


def build_chunks(blocks: list, max_chars: int = 7000, max_blocks: int = 8, context_chars: int = 700) -> list:
    units = []
    for b in blocks:
        parts = _split_long(b.text, max_chars)
        for i, part in enumerate(parts):
            units.append({"block_id": b.block_id, "part": i + 1, "parts": len(parts), "heading": b.heading,
                          "scene_number": b.scene_number, "page_start": b.page_start, "page_end": b.page_end,
                          "heading_ok": b.heading_ok, "flag": b.flag, "text": part})
    chunks, cur, cur_chars = [], [], 0
    prev_text = ""

    def flush():
        nonlocal cur, cur_chars, prev_text
        if not cur:
            return
        idx = len(chunks) + 1
        raw = "\n\n".join(u["text"] for u in cur)
        chunks.append(Chunk(f"C{idx:03d}", idx, cur, prev_text[-context_chars:] if prev_text else "",
                            min(u["page_start"] for u in cur), max(u["page_end"] for u in cur)))
        prev_text = raw
        cur, cur_chars = [], 0

    for u in units:
        distinct = len({x["block_id"] for x in cur})
        new_block = not cur or cur[-1]["block_id"] != u["block_id"]
        if cur and (cur_chars + len(u["text"]) > max_chars or (new_block and distinct >= max_blocks)):
            flush()
        cur.append(u)
        cur_chars += len(u["text"])
    flush()
    return chunks


# ---- deterministic dialogue-cue detection, used to cross-check LLM output ----
_NOT_CUES = re.compile(r"^(FADE|CUT|DISSOLVE|SMASH|MATCH|INTERCUT|TITLE|SUPER|END|THE END|BACK TO|CONTINUED|"
                       r"FLASHBACK|INSERT|ANGLE|CLOSE|WIDE|LATER|MONTAGE|SERIES OF|BEGIN|RESUME)\b")


def extract_speakers(text: str) -> dict:
    """Return {NAME: extension_or_''} for ALL-CAPS cue lines followed by dialogue."""
    lines = text.split("\n")
    found = {}
    for i, ln in enumerate(lines[:-1]):
        s = ln.strip()
        if not s or match_heading(s) or len(s) > 40:
            continue
        m = re.match(r"^([A-Z][A-Z0-9 .'\-]{0,30}?)\s*(\((?:V\.?O\.?|O\.?S\.?|O\.?C\.?|CONT'?D\.?)\))?$", s)
        if not m:
            continue
        name = m.group(1).strip(" .")
        if not name or _NOT_CUES.match(name) or name.endswith(":") or len(name.split()) > 4:
            continue
        if not lines[i + 1].strip():
            continue
        ext = (m.group(2) or "").upper()
        found.setdefault(name, "voice" if re.search(r"V\.?O|O\.?S", ext) else "")
        if found[name] == "voice" and not re.search(r"V\.?O|O\.?S", ext):
            found[name] = ""
    return found
