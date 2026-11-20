"""Robust JSON extraction/repair and schema validation for LLM output."""
import json
import re


class ParseError(Exception):
    pass


def _strip_reasoning(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text


def _balance(s: str) -> str:
    """Close a truncated JSON document: end open string, drop dangling key/comma, close brackets."""
    stack, in_str, esc = [], False, False
    for ch in s:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]" and stack:
            stack.pop()
    if in_str:
        s += '"'
    s = re.sub(r",\s*$", "", s)
    s = re.sub(r',?\s*"[^"]*"\s*:\s*$', "", s)   # dangling key with no value
    s = re.sub(r",\s*$", "", s)
    return s + "".join(reversed(stack))


def extract_json(text: str):
    if not text or not text.strip():
        raise ParseError("Empty response from the model.")
    t = _strip_reasoning(text)
    fence = re.search(r"```(?:json)?\s*(.*?)(?:```|$)", t, re.S)
    if fence and fence.group(1).strip():
        t = fence.group(1)
    starts = [i for i in (t.find("{"), t.find("[")) if i >= 0]
    if not starts:
        raise ParseError("No JSON object found in the model response.")
    body = t[min(starts):]
    end = max(body.rfind("}"), body.rfind("]"))
    attempts = []
    if end >= 0:
        attempts.append(body[:end + 1])
    attempts.append(body)
    last = None
    for cand in attempts:
        for variant in (cand, re.sub(r",\s*([}\]])", r"\1", cand), _balance(re.sub(r",\s*([}\]])", r"\1", cand))):
            try:
                return json.loads(variant)
            except json.JSONDecodeError as exc:
                last = exc
    raise ParseError(f"Invalid JSON from the model ({last}).")


def validate(model_cls, data) -> dict:
    """Validate with Pydantic and return a plain dict (never raw LLM output)."""
    try:
        from pydantic import ValidationError
    except ImportError as exc:  # pragma: no cover
        raise ParseError("pydantic is not installed.") from exc
    try:
        return model_cls.model_validate(data).model_dump()
    except ValidationError as exc:
        errs = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:6])
        raise ParseError(f"Response failed schema validation: {errs}") from exc


def parse_model(text: str, model_cls) -> dict:
    return validate(model_cls, extract_json(text))
