import re
from core.chunking_engine import extract_speakers, match_heading


def make_script(n_scenes: int) -> str:
    locs = ["KITCHEN", "ROOFTOP", "WAREHOUSE", "CAFE", "PARK", "OFFICE"]
    out = ["TITLE PAGE", "", "FADE IN:", ""]
    for i in range(1, n_scenes + 1):
        ie = "INT." if i % 3 else "EXT."
        tod = "NIGHT" if i % 4 == 0 else "DAY"
        a, b = ["ANNA", "BEN", "CARLA", "DAVE"][i % 4], ["ANNA", "BEN", "CARLA", "DAVE"][(i + 1) % 4]
        out += [f"{ie} {locs[i % len(locs)]} - {tod}", "", f"{a.title()} enters and looks around the {locs[i % len(locs)].lower()}.", "",
                a, f"Line number {i} of the script.", "", b, "Reply to that.", ""]
    return "\n".join(out)


class FakeClient:
    """TEST DOUBLE ONLY: deterministic stand-in for the NVIDIA API. Never used by the app."""
    model = "fake"

    def __init__(self, drop_block=None, fail_chunks=0):
        self.drop_block, self.fail_chunks, self.calls = drop_block, fail_chunks, 0

    def chat_json(self, messages, model_cls, **kw):
        from ai.nvidia_client import NvidiaError
        self.calls += 1
        body = messages[-1]["content"]
        if "Chunk summaries" in body:
            return {"synopsis": "A test story.", "genre": "Drama", "main_plot": "p", "subplots": [], "protagonist": "Maya",
                    "antagonist": "", "supporting_characters": [], "beginning": "b", "middle": "m", "ending": "e",
                    "major_events": ["x"], "turning_points": [], "emotional_sequences": [], "uncertainty_notes": []}
        if self.fail_chunks > 0:
            self.fail_chunks -= 1
            raise NvidiaError("simulated outage")
        scenes, chars = [], {}
        for m in re.finditer(r"### SCENE BLOCK (B\d+) \|.*?\n(.*?)\n### END \1", body, re.S):
            bid, text = m.group(1), m.group(2)
            if bid == self.drop_block:
                continue
            sp = extract_speakers(text)
            present = [n for n, k in sp.items() if not k]
            if bid == "B001":
                present.append("GHOST")  # hallucination the validator must remove
            props = [{"name": "phone", "source_type": "EXPLICIT"}] if "PHONE" in text.upper() else []
            scenes.append({"block_id": bid, "characters_present": present, "characters_voice_only": [], "characters_mentioned": [],
                           "description": f"Scene {bid}", "main_action": "act", "has_dialogue": bool(sp), "props": props,
                           "costumes": [], "vehicles": [], "special_effects": [], "equipment": [{"name": "camera", "source_type": "RECOMMENDED"}],
                           "complexity": "Low", "confidence": 0.9, "evidence": "", "int_ext": "", "time_of_day": "", "location": "",
                           "needs_review": False, "review_reason": ""})
            for n in present:
                chars[n] = {"name": n, "description": f"{n} desc", "char_type": "Lead", "relationships": []}
        return {"chunk_summary": f"Summary of {len(scenes)} scenes.", "scenes": scenes, "characters": list(chars.values())}

    def chat(self, messages, **kw):
        return "- Consider combining the two night scenes.\n- Confirm actor availability."
