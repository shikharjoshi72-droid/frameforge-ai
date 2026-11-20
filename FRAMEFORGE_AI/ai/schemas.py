"""Pydantic schemas used to validate every LLM response before it touches the database."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

SRC = {"EXPLICIT", "INFERRED", "RECOMMENDED"}


def _to_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    return v


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ResourceItem(_Base):
    name: str
    source_type: str = "INFERRED"
    description: str = ""
    quantity: Optional[str] = None
    character: str = ""
    notes: str = ""

    @field_validator("source_type", mode="before")
    @classmethod
    def _src(cls, v):
        v = str(v or "").strip().upper()
        return v if v in SRC else "INFERRED"

    @field_validator("quantity", mode="before")
    @classmethod
    def _qty(cls, v):
        return None if v in (None, "", "unknown", "null") else str(v)

    @field_validator("description", "character", "notes", mode="before")
    @classmethod
    def _s(cls, v):
        return "" if v is None else str(v)


def _items(v):
    out = []
    for x in _to_list(v):
        if isinstance(x, str):
            out.append({"name": x, "source_type": "INFERRED"})
        elif isinstance(x, dict) and str(x.get("name", "")).strip():
            out.append(x)
    return out


class SceneAI(_Base):
    block_id: str
    characters_present: list[str] = Field(default_factory=list)
    characters_voice_only: list[str] = Field(default_factory=list)
    characters_mentioned: list[str] = Field(default_factory=list)
    description: str = ""
    main_action: str = ""
    has_dialogue: bool = False
    props: list[ResourceItem] = Field(default_factory=list)
    costumes: list[ResourceItem] = Field(default_factory=list)
    vehicles: list[ResourceItem] = Field(default_factory=list)
    special_effects: list[ResourceItem] = Field(default_factory=list)
    equipment: list[ResourceItem] = Field(default_factory=list)
    complexity: str = ""
    confidence: float = 0.5
    evidence: str = ""
    int_ext: str = ""
    time_of_day: str = ""
    location: str = ""
    needs_review: bool = False
    review_reason: str = ""

    @field_validator("characters_present", "characters_voice_only", "characters_mentioned", mode="before")
    @classmethod
    def _names(cls, v):
        return [str(x).strip() for x in _to_list(v) if str(x).strip()]

    @field_validator("props", "costumes", "vehicles", "special_effects", "equipment", mode="before")
    @classmethod
    def _res(cls, v):
        return _items(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _conf(cls, v):
        try:
            f = float(v)
        except (TypeError, ValueError):
            return 0.5
        return max(0.0, min(1.0, f / 100 if f > 1 else f))

    @field_validator("description", "main_action", "evidence", "int_ext", "time_of_day", "location",
                     "review_reason", "complexity", mode="before")
    @classmethod
    def _txt(cls, v):
        return "" if v is None else str(v)

    @field_validator("has_dialogue", "needs_review", mode="before")
    @classmethod
    def _bool(cls, v):
        return v if isinstance(v, bool) else str(v).strip().lower() in ("true", "yes", "1")


class CharacterAI(_Base):
    name: str
    description: str = ""
    char_type: str = ""
    relationships: list[str] = Field(default_factory=list)

    @field_validator("relationships", mode="before")
    @classmethod
    def _rel(cls, v):
        return [str(x) if not isinstance(x, dict) else " ".join(str(y) for y in x.values())
                for x in _to_list(v)]


class ChunkResult(_Base):
    chunk_summary: str = ""
    scenes: list[SceneAI] = Field(default_factory=list)
    characters: list[CharacterAI] = Field(default_factory=list)

    @field_validator("characters", mode="before")
    @classmethod
    def _chars(cls, v):
        return [{"name": x} if isinstance(x, str) else x for x in _to_list(v)]


class SceneRedo(_Base):
    """Single-scene re-analysis (same fields as SceneAI, block_id optional)."""
    scene: SceneAI


class StoryAnalysisAI(_Base):
    synopsis: str = ""
    genre: str = ""
    main_plot: str = ""
    subplots: list[str] = Field(default_factory=list)
    protagonist: str = ""
    antagonist: str = ""
    supporting_characters: list[str] = Field(default_factory=list)
    beginning: str = ""
    middle: str = ""
    ending: str = ""
    major_events: list[str] = Field(default_factory=list)
    turning_points: list[str] = Field(default_factory=list)
    emotional_sequences: list[str] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)

    @field_validator("subplots", "supporting_characters", "major_events", "turning_points",
                     "emotional_sequences", "uncertainty_notes", mode="before")
    @classmethod
    def _l(cls, v):
        return [str(x) for x in _to_list(v)]

    @field_validator("synopsis", "genre", "main_plot", "protagonist", "antagonist", "beginning", "middle",
                     "ending", mode="before")
    @classmethod
    def _t(cls, v):
        return "" if v is None else str(v)
