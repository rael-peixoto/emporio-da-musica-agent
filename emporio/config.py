"""Paths, store time zone and runtime settings.

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


@dataclass(frozen=True)
class Settings:
    model: str
    effort: str


def load_settings() -> Settings:
    """Read settings from the environment, after loading an optional .env file."""
    load_dotenv(PROJECT_ROOT / ".env")
    model = os.getenv("MODEL", "").strip() or DEFAULT_MODEL
    effort = os.getenv("EFFORT", "").strip().lower() or DEFAULT_EFFORT
    if effort not in EFFORT_LEVELS:
        raise ValueError(f"EFFORT must be one of {', '.join(EFFORT_LEVELS)}; got {effort!r}")
    return Settings(model=model, effort=effort)


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
