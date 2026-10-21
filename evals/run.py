"""Run the scenario suite against the real model and report pass/fail, tokens and cost.

Usage (direct mode, needs ANTHROPIC_API_KEY in .env):
    python -m evals.run [--model claude-haiku-5-5] [--only id1,id2]

Writes evals/results/<model>.md with the summary and every transcript.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from emporio.agent import Agent
from emporio.catalog import Catalog
from emporio.config import load_settings, resolve_now
from emporio.llm import make_client
from emporio.tools import ToolBox
from evals.scenarios import DEFAULT_NOW, SCENARIOS

RESULTS_DIR = Path(__file__).parent / "results"


def check(scenario: dict, replies: list[str], tools_called: set[str]) -> list[str]:
    text = "\n".join(replies).casefold()
    failures = []
    for s in scenario.get("contains", []):
        if s.casefold() not in text:
            failures.append(f"missing {s!r}")
    for group in scenario.get("any_of", []):
        if not any(s.casefold() in text for s in group):
            failures.append(f"none of {group}")
    for s in scenario.get("absent", []):
        if s.casefold() in text:
            failures.append(f"must not contain {s!r}")
    for tool in scenario.get("tools", []):
        if tool not in tools_called:
            failures.append(f"did not call {tool}")
    for tool in scenario.get("no_tools", []):
        if tool in tools_called:
            failures.append(f"must not call {tool}")
    return failures


def run(model: str | None, only: set[str] | None) -> int:
    settings = load_settings()
    if settings.backend != "direct":
        print("Evals run in direct mode: set ANTHROPIC_API_KEY in .env", file=sys.stderr)
        return 2
    if model:
        settings = replace(settings, model=model)
    client = make_client(settings)
    catalog = Catalog.load()
    handoffs = Path(tempfile.mkdtemp()) / "handoffs.jsonl"  # keep eval handoffs out of logs/

    rows, transcripts, total_cost, passed = [], [], 0.0, 0
    scenarios = [s for s in SCENARIOS if not only or s["id"] in only]
    for scenario in scenarios:
        now = resolve_now(scenario.get("now", DEFAULT_NOW))
        agent = Agent(client, settings, catalog, now, ToolBox(catalog, now, handoffs))
        replies, tools_called, cost, started = [], set(), 0.0, time.monotonic()
        transcript = [f"### {scenario['id']} (now {now:%d/%m/%Y %H:%M})", ""]
        for message in scenario["messages"]:
            turn = agent.send(message)
            replies.append(turn.reply)
            tools_called |= {c.name for c in turn.tool_calls}
            cost += turn.cost_usd
            calls = ", ".join(c.name for c in turn.tool_calls) or "none"
            transcript += [f"**Cliente:** {message}", "", f"_tools: {calls}_", "",
                           f"**Assistente:** {turn.reply}", ""]
        failures = check(scenario, replies, tools_called)
        ok = not failures
        passed += ok
        total_cost += cost
        seconds = time.monotonic() - started
        rows.append(f"| {scenario['id']} | {'PASS' if ok else 'FAIL'} | {'; '.join(failures)} "
                    f"| {seconds:.1f}s | {cost:.4f} |")
        transcripts += transcript + [f"Result: {'PASS' if ok else 'FAIL ' + '; '.join(failures)}", ""]
        print(f"{'PASS' if ok else 'FAIL'}  {scenario['id']}  {'; '.join(failures)}  (US$ {cost:.4f})")

    summary = [
        f"# Scenario evaluation: `{settings.model}` (effort `{settings.effort}`)",
        "",
        f"**{passed}/{len(scenarios)} passed** · estimated cost US$ {total_cost:.4f}",
        "",
        "| Scenario | Result | Failed checks | Time | US$ |",
        "|---|---|---|---|---|",
        *rows,
        "",
        "## Transcripts",
        "",
    ]
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{settings.model}.md"
    out.write_text("\n".join(summary + transcripts), encoding="utf-8")
    print(f"\n{passed}/{len(scenarios)} passed · estimated cost US$ {total_cost:.4f} · {out}")
    return 0 if passed == len(scenarios) else 1


def main() -> int:
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="python -m evals.run")
    parser.add_argument("--model", help="override MODEL, e.g. claude-sonnet-5-5")
    parser.add_argument("--only", help="comma-separated scenario ids")
    args = parser.parse_args()
    only = set(args.only.split(",")) if args.only else None
    return run(args.model, only)


if __name__ == "__main__":
    raise SystemExit(main())
