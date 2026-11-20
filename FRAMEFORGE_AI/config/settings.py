"""Environment-driven configuration. API keys are never logged or rendered."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "frameforge.db"
UPLOAD_DIR = DATA_DIR / "uploads"
BLACKBOOK_DIR = BASE_DIR / "generated" / "blackbooks"
FONT_DIR = BASE_DIR / "assets" / "fonts"


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    nvidia_api_key: str
    nvidia_model: str
    nvidia_base_url: str
    request_timeout: int
    max_retries: int
    max_upload_mb: int
    chunk_max_chars: int
    chunk_max_blocks: int
    context_chars: int
    max_tokens: int
    disable_thinking: bool

    @property
    def has_key(self) -> bool:
        return bool(self.nvidia_api_key.strip())


def get_settings() -> Settings:
    return Settings(
        nvidia_api_key=os.getenv("NVIDIA_API_KEY", "").strip(),
        nvidia_model=os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-nano-30b-a3b").strip(),
        nvidia_base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip(),
        request_timeout=_int("NVIDIA_TIMEOUT", 120),
        max_retries=_int("NVIDIA_MAX_RETRIES", 3),
        max_upload_mb=_int("MAX_UPLOAD_MB", 15),
        chunk_max_chars=_int("CHUNK_MAX_CHARS", 7000),
        chunk_max_blocks=_int("CHUNK_MAX_BLOCKS", 8),
        context_chars=_int("CHUNK_CONTEXT_CHARS", 700),
        max_tokens=_int("NVIDIA_MAX_TOKENS", 6000),
        disable_thinking=os.getenv("NVIDIA_DISABLE_THINKING", "1") != "0",
    )
