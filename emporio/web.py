"""Local web chat for testers: a WhatsApp-style page plus a "behind the scenes" console tab.

It serves one page on 127.0.0.1 only and runs the same Agent as the CLI, in direct or proxy mode.

Usage: python -m emporio.web [--mode proxy|direct] [--now ISO_DATETIME] [--port 8000]
"""

from __future__ import annotations

import argparse
import secrets
import sys
import threading
import uuid
import webbrowser
from collections.abc import Callable
from pathlib import Path

import anthropic
import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from emporio import llm
from emporio.agent import Agent, Turn
from emporio.catalog import Catalog
from emporio.cli import iso_datetime
from emporio.config import BACKENDS, Settings, load_settings, resolve_now
from emporio.messages import api_error_message

PAGE = Path(__file__).parent / "static" / "index.html"
MAX_SESSIONS = 20


class ChatRequest(BaseModel):
    session_id: str
    message: str


class Session:
    def __init__(self, agent: Agent):
        self.agent = agent
        self.turns: list[dict] = []
        self.busy = threading.Lock()  # one message at a time per conversation


def turn_view(turn: Turn) -> dict:
    return {
        "user": turn.user,
        "reply": turn.reply,
        "tool_calls": [{"name": c.name, "input": c.input, "output": c.output, "is_error": c.is_error}
                       for c in turn.tool_calls],
        "tokens": turn.tokens,
        "api_calls": turn.api_calls,
        "cost_usd": turn.cost_usd,
        "model": turn.model,
    }


def create_app(agent_factory: Callable[[], Agent], settings: Settings, simulated: bool,
               token: str | None = None) -> FastAPI:
    # Every API call must carry this token. Other websites open in the same browser can't read
    # the page, so they can't learn it, and so can't make this server spend API credits.
    token = token or secrets.token_urlsafe(24)
    sessions: dict[str, Session] = {}
    lock = threading.Lock()
    app = FastAPI(title="Empório da Música - demo local", docs_url=None, redoc_url=None,
                  openapi_url=None)

    def authorize(given: str | None) -> None:
        if not secrets.compare_digest((given or "").encode(), token.encode()):
            raise HTTPException(403, "invalid page token")

    def get_session(session_id: str) -> Session:
        session = sessions.get(session_id)
        if session is None:
            raise HTTPException(404, "unknown session")
        return session

    @app.get("/", response_class=HTMLResponse)
    def index():
        return PAGE.read_text(encoding="utf-8").replace("__PAGE_TOKEN__", token)

    @app.post("/api/session")
    def new_session(x_page_token: str | None = Header(default=None)):
        authorize(x_page_token)
        with lock:
            if len(sessions) >= MAX_SESSIONS:
                sessions.pop(next(iter(sessions)))  # drop the oldest conversation
            session_id = uuid.uuid4().hex
            sessions[session_id] = Session(agent_factory())
        agent = sessions[session_id].agent
        return {"session_id": session_id, "mode": settings.backend,
                "now": agent.now.strftime("%d/%m/%Y %H:%M"), "simulated": simulated}

    @app.post("/api/chat")
    async def chat(request: ChatRequest, x_page_token: str | None = Header(default=None)):
        authorize(x_page_token)
        session = get_session(request.session_id)
        if not session.busy.acquire(blocking=False):
            raise HTTPException(409, "still answering the previous message")
        try:
            turn = await run_in_threadpool(session.agent.send, request.message)
        except anthropic.APIError as exc:
            return JSONResponse({"error": api_error_message(exc)}, status_code=502)
        finally:
            session.busy.release()
        view = turn_view(turn)
        session.turns.append(view)
        return {**view, "session_cost_usd": session.agent.total_cost_usd}

    @app.get("/api/history")
    def history(session_id: str, x_page_token: str | None = Header(default=None)):
        authorize(x_page_token)
        session = get_session(session_id)
        return {"turns": session.turns, "session_cost_usd": session.agent.total_cost_usd,
                "mode": settings.backend, "now": session.agent.now.strftime("%d/%m/%Y %H:%M"),
                "simulated": simulated}

    return app


def main(argv: list[str] | None = None) -> int:
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="python -m emporio.web",
        description="Local WhatsApp-style web chat with a behind-the-scenes console tab.",
    )
    parser.add_argument("--mode", choices=BACKENDS, help="proxy (access code) or direct (own key)")
    parser.add_argument("--now", type=iso_datetime, metavar="ISO_DATETIME",
                        help="simulate the current date/time in Campo Grande")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true", help="don't open the browser")
    args = parser.parse_args(argv)

    try:
        settings = load_settings(backend=args.mode)
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    print(f"Modo: {settings.backend}")
    if settings.backend == "proxy":
        print("Conectando ao servidor (se estiver dormindo, pode levar até 1 minuto)...")
        if not llm.wake_proxy(settings.proxy_url):
            print("Não consegui conectar ao servidor. Tente de novo mais tarde.", file=sys.stderr)
            return 1

    client = llm.make_client(settings)
    catalog = Catalog.load()
    app = create_app(lambda: Agent(client, settings, catalog, args.now or resolve_now()),
                     settings, simulated=bool(args.now))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Abra {url} no navegador. Ctrl+C encerra.")
    if not args.no_browser:
        threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
