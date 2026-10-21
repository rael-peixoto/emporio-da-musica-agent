"""Paths, store time zone, runtime settings and usage limits.

The API key is deliberately not stored here: the Anthropic SDK reads
ANTHROPIC_API_KEY from the environment, so the key never passes through
our code and cannot be printed or logged by accident.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
LOGS_DIR = PROJECT_ROOT / "logs"

# Campo Grande/MS is UTC-4 with no daylight saving time.
STORE_TZ = ZoneInfo("America/Campo_Grande")

DEFAULT_MODEL = "claude-haiku-5-5"
DEFAULT_EFFORT = "low"
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
BACKENDS = ("direct", "proxy")

# Hosted proxy used when no API key is configured (see proxy/ and render.yaml).
DEFAULT_PROXY_URL = "https://emporio-proxy.onrender.com"

# Usage limits that keep a session from running up costs (both modes)
MAX_TOKENS = 2048  # per model response, thinking included
MAX_INPUT_CHARS = 1500  # per customer message
MAX_TOOL_ROUNDS = 5  # tool calls the model may chain before it must answer
MAX_TURNS = 50  # customer messages per session
SESSION_BUDGET_USD = 0.50  # estimated spend per session


@dataclass(frozen=True)
class Settings:
    model: str
    effort: str
    backend: str  # "direct" (own API key) or "proxy" (hosted proxy + access code)
    proxy_url: str
    access_code: str | None


def load_settings(env_file: Path | None = PROJECT_ROOT / ".env") -> Settings:
    """Read settings from the environment, after loading an optional .env file."""
    if env_file:
        load_dotenv(env_file)
    model = os.getenv("MODEL", "").strip() or DEFAULT_MODEL
    effort = os.getenv("EFFORT", "").strip().lower() or DEFAULT_EFFORT
    if effort not in EFFORT_LEVELS:
        raise ValueError(f"EFFORT must be one of {', '.join(EFFORT_LEVELS)}; got {effort!r}")

    has_key = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    backend = os.getenv("LLM_BACKEND", "").strip().lower() or ("direct" if has_key else "proxy")
    if backend not in BACKENDS:
        raise ValueError(f"LLM_BACKEND must be one of {', '.join(BACKENDS)}; got {backend!r}")
    proxy_url = (os.getenv("PROXY_URL", "").strip() or DEFAULT_PROXY_URL).rstrip("/")
    access_code = os.getenv("EMPORIO_ACCESS_CODE", "").strip() or None

    if backend == "direct" and not has_key:
        raise ValueError("direct mode needs ANTHROPIC_API_KEY in .env")
    if backend == "proxy" and not access_code:
        raise ValueError(
            "proxy mode needs EMPORIO_ACCESS_CODE in .env (sent with the submission); "
            "or set ANTHROPIC_API_KEY to use your own key"
        )
    if backend == "proxy" and not proxy_url:
        raise ValueError("proxy mode needs PROXY_URL in .env")
    return Settings(model, effort, backend, proxy_url, access_code)


def resolve_now(iso_datetime: str | None = None) -> datetime:
    """Return the current time in the store's time zone, or a simulated one.

    A naive ISO value (e.g. "2026-03-25T10:00") is read as Campo Grande local
    time; an aware value is converted to it.
    """
    if iso_datetime is None:
        return datetime.now(STORE_TZ)
    moment = datetime.fromisoformat(iso_datetime)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=STORE_TZ)
    return moment.astimezone(STORE_TZ)
