"""Terminal chat interface."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from emporio.config import load_settings, resolve_now


def _iso_datetime(value: str) -> datetime:
    try:
        return resolve_now(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid date/time {value!r}; use ISO format, e.g. 2026-03-25T10:00"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m emporio",
        description="Chat with the Empório da Música virtual assistant (replies in pt-BR).",
    )
    parser.add_argument(
        "--now",
        type=_iso_datetime,
        metavar="ISO_DATETIME",
        help="simulate the current date/time in Campo Grande, e.g. 2026-03-25T10:00 "
        "(default: the real clock)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="print every tool call and its result",
    )
    parser.add_argument(
        "--save",
        type=Path,
        metavar="PATH",
        help="write the conversation, including tool calls, to a Markdown file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    now = args.now or resolve_now()
    print(f"model={settings.model} effort={settings.effort} now={now.isoformat()}")
    print("The chat loop is not implemented yet (stage 4).", file=sys.stderr)
    return 1
