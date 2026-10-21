"""Terminal chat interface."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import anthropic

from emporio import llm
from emporio.agent import Agent, Turn
from emporio.catalog import Catalog
from emporio.config import BACKENDS, Settings, load_settings, resolve_now
from emporio.messages import api_error_message

EXIT_WORDS = {"sair", "exit", "quit", "tchau"}
MODE_LABELS = {"direct": "direto (sua chave da API)", "proxy": "proxy (servidor da Empório)"}


def iso_datetime(value: str) -> datetime:
    """argparse type for --now (shared with the web UI)."""
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
        type=iso_datetime,
        metavar="ISO_DATETIME",
        help="simulate the current date/time in Campo Grande, e.g. 2026-03-25T10:00 "
        "(default: the real clock)",
    )
    parser.add_argument(
        "--mode",
        choices=BACKENDS,
        help="proxy: use the hosted proxy (needs EMPORIO_ACCESS_CODE); direct: use your own "
        "ANTHROPIC_API_KEY (default: direct if a key is set, otherwise proxy)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="print every tool call, its result, tokens and estimated cost",
    )
    parser.add_argument(
        "--save",
        type=Path,
        metavar="PATH",
        help="write the conversation, including tool calls, to a Markdown file",
    )
    return parser


class Transcript:
    """Markdown record of a session, rewritten after every turn so nothing is lost on exit."""

    def __init__(self, path: Path, settings: Settings, now: datetime, simulated: bool):
        self.path = path
        self.settings = settings
        self.when = f"{'simulada' if simulated else 'real'}: {now:%d/%m/%Y %H:%M} (Campo Grande)"
        self.lines: list[str] = []
        self.cost_usd = 0.0

    def add(self, turn: Turn) -> None:
        self.cost_usd += turn.cost_usd
        header = [
            "# Conversa com o assistente da Empório da Música",
            "",
            f"- Data/hora {self.when}",
            f"- Modelo: `{turn.model or self.settings.model}` · modo: {self.settings.backend}",
            f"- Custo estimado da conversa: US$ {self.cost_usd:.4f}",
            "",
        ]
        self.lines += [f"**Cliente:** {turn.user}", ""]
        for call in turn.tool_calls:
            args = json.dumps(call.input, ensure_ascii=False)
            self.lines += [
                "<details><summary>Consulta: <code>" + f"{call.name}({args})" + "</code></summary>",
                "",
                "```json",
                call.output,
                "```",
                "</details>",
                "",
            ]
        self.lines += [f"**Assistente:** {turn.reply}", ""]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(header + self.lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    # Windows uses a legacy code page for pipes; scripted conversations are UTF-8 files
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not sys.stdin.isatty():
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(backend=args.mode)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    now = args.now or resolve_now()

    print("Empório da Música · assistente virtual")
    print(f"Modo: {MODE_LABELS[settings.backend]} · digite 'sair' para encerrar")
    if args.now:
        print(f"Data/hora simulada: {now:%d/%m/%Y %H:%M}")
    if settings.backend == "proxy":
        print("Conectando ao servidor (se estiver dormindo, pode levar até 1 minuto)...")
        if not llm.wake_proxy(settings.proxy_url):
            print("Não consegui conectar ao servidor. Tente de novo mais tarde.", file=sys.stderr)
            return 1

    agent = Agent(llm.make_client(settings), settings, Catalog.load(), now)
    transcript = Transcript(args.save, settings, now, bool(args.now)) if args.save else None
    while True:
        try:
            text = input("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in EXIT_WORDS:
            break
        try:
            turn = agent.send(text)
        except anthropic.APIError as exc:
            print(f"\n[{api_error_message(exc)}]")
            continue
        if args.debug:
            for call in turn.tool_calls:
                print(f"  [ferramenta] {call.name}({json.dumps(call.input, ensure_ascii=False)})")
                print(f"  [resultado] {call.output[:500]}")
            tokens = " ".join(f"{k}={v}" for k, v in turn.tokens.items())
            print(f"  [uso] {turn.api_calls} chamada(s) · {tokens} · US$ {turn.cost_usd:.5f}")
        print(f"\nAssistente: {turn.reply}")
        if transcript:
            transcript.add(turn)

    print("\nAté logo!")
    if args.debug:
        print(f"Custo estimado desta sessão: US$ {agent.total_cost_usd:.4f}")
    return 0
