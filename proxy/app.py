"""Hosted proxy: reviewers use the agent without an API key, and the author's key never leaves
the server.

It exposes the Anthropic Messages API path (POST /v1/messages), so the agent's standard SDK
client works with only its base URL changed. Everything that drives cost is decided here, not
by the client: the model, effort, max_tokens, system prompt and tools are replaced with the
server's own copies, which also stops the proxy from being used as a general Claude endpoint.

Run with:  uvicorn --factory proxy.app:create_app --no-access-log
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import threading
import time
from collections import deque
from datetime import date, datetime, timezone

import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from emporio import config
from emporio.llm import estimate_cost
from emporio.prompt import LANGUAGE_REMINDER, static_prompt
from emporio.tools import TOOLS

log = logging.getLogger("emporio.proxy")

MAX_BODY_BYTES = 512 * 1024
MAX_MESSAGES = 100
MAX_CONTEXT_CHARS = 600
MAX_TOOL_RESULT_CHARS = 20_000
MIN_ACCESS_CODE_LENGTH = 16
CONTEXT_PREFIX = "# Contexto atual"


def api_error(status: int, error_type: str, message: str, headers: dict | None = None):
    """Anthropic-style error body, so the client SDK raises its usual typed exceptions."""
    body = {"type": "error", "error": {"type": error_type, "message": message}}
    return JSONResponse(body, status_code=status, headers=headers)


class RateLimiter:
    """Global sliding window. Per-IP limits are not used: X-Forwarded-For can be spoofed."""

    def __init__(self, per_minute: int, clock=time.monotonic):
        self.per_minute = per_minute
        self.clock = clock
        self.hits: deque[float] = deque()
        self.lock = threading.Lock()

    def retry_after(self) -> int:
        """0 if the request may proceed (and records it); otherwise seconds to wait."""
        with self.lock:
            now = self.clock()
            while self.hits and now - self.hits[0] >= 60:
                self.hits.popleft()
            if len(self.hits) < self.per_minute:
                self.hits.append(now)
                return 0
            return max(1, int(60 - (now - self.hits[0])) + 1)


class DailyBudget:
    """Estimated spend per UTC day, in memory (resets on restart; the Anthropic workspace
    spend limit is the persistent backstop)."""

    def __init__(self, limit_usd: float, today=lambda: datetime.now(timezone.utc).date()):
        self.limit_usd = limit_usd
        self.today = today
        self.day: date | None = None
        self.spent = 0.0
        self.lock = threading.Lock()

    def _roll(self) -> None:
        if self.day != self.today():
            self.day, self.spent = self.today(), 0.0

    def exhausted(self) -> bool:
        with self.lock:
            self._roll()
            return self.spent >= self.limit_usd

    def add(self, cost: float) -> float:
        with self.lock:
            self._roll()
            self.spent += cost
            return self.spent


def presented_code(request: Request) -> str:
    """The client's access code. The Anthropic SDK sends its key either as x-api-key or, in
    newer versions, as "Authorization: Bearer <key>"; accept both."""
    if code := request.headers.get("x-api-key"):
        return code.strip()
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    return token.strip() if scheme.lower() == "bearer" else ""


def _texts(content) -> list[str]:
    if isinstance(content, str):
        return [content]
    return [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]


def validate(payload) -> str | None:
    """Return a reason to reject the request, or None if it looks like our agent's request."""
    if not isinstance(payload, dict):
        return "body must be a JSON object"
    messages = payload.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        return f"messages must be a list of 1 to {MAX_MESSAGES} items"
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in ("user", "assistant", "system"):
            return "each message needs role user, assistant or system"
        content = message.get("content")
        if message["role"] == "system" and content != LANGUAGE_REMINDER:
            return "unexpected system message"  # only the agent's fixed reminder is allowed
        if not isinstance(content, (str, list)):
            return "message content must be text or a list of blocks"
        if message["role"] == "user":
            if any(len(t) > config.MAX_INPUT_CHARS for t in _texts(content)):
                return f"user text is limited to {config.MAX_INPUT_CHARS} characters"
            if isinstance(content, list) and any(
                isinstance(b, dict) and b.get("type") == "tool_result"
                and len(json.dumps(b.get("content", ""))) > MAX_TOOL_RESULT_CHARS
                for b in content
            ):
                return "tool result too large"
    if context_block(payload) is None:
        return "unexpected system prompt"
    return None


def context_block(payload: dict) -> str | None:
    """The only part of the system prompt the client may supply: the date/time block."""
    system = payload.get("system")
    if not isinstance(system, list) or not system or not isinstance(system[-1], dict):
        return None
    text = system[-1].get("text")
    if not isinstance(text, str) or not text.startswith(CONTEXT_PREFIX):
        return None
    return text if len(text) <= MAX_CONTEXT_CHARS else None


def upstream_params(payload: dict, model: str, effort: str) -> dict:
    params = {
        "model": model,
        "max_tokens": config.MAX_TOKENS,
        "output_config": {"effort": effort},
        "system": [
            {"type": "text", "text": static_prompt(), "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": context_block(payload)},
        ],
        "tools": TOOLS,
        "messages": payload["messages"],
    }
    if payload.get("tool_choice") == {"type": "none"}:  # the agent's forced-answer round
        params["tool_choice"] = {"type": "none"}
    return params


def create_app(
    upstream: anthropic.Anthropic | None = None,
    access_code: str | None = None,
    requests_per_minute: int | None = None,
    daily_budget_usd: float | None = None,
) -> FastAPI:
    # Strip: a value pasted into a dashboard or written by a script may carry whitespace
    access_code = (access_code or os.environ.get("EMPORIO_ACCESS_CODE", "")).strip()
    if len(access_code) < MIN_ACCESS_CODE_LENGTH:
        raise RuntimeError(f"EMPORIO_ACCESS_CODE must be set (at least {MIN_ACCESS_CODE_LENGTH} chars)")
    if upstream is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY must be set")
        upstream = anthropic.Anthropic(timeout=60, max_retries=1)
    model = os.environ.get("PROXY_MODEL", config.DEFAULT_MODEL)
    effort = os.environ.get("PROXY_EFFORT", config.DEFAULT_EFFORT)
    limiter = RateLimiter(requests_per_minute or int(os.environ.get("PROXY_REQUESTS_PER_MINUTE", "30")))
    budget = DailyBudget(daily_budget_usd or float(os.environ.get("PROXY_DAILY_BUDGET_USD", "1.00")))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    app = FastAPI(title="Empório da Música proxy", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/messages")
    async def messages(request: Request):
        if not hmac.compare_digest(presented_code(request).encode(), access_code.encode()):
            return api_error(401, "authentication_error", "invalid access code")
        body = await request.body()
        if len(body) > MAX_BODY_BYTES:
            return api_error(413, "request_too_large", "request body too large")
        try:
            payload = json.loads(body)
        except ValueError:
            return api_error(400, "invalid_request_error", "body is not valid JSON")
        if problem := validate(payload):
            return api_error(400, "invalid_request_error", problem)
        if wait := limiter.retry_after():
            return api_error(429, "rate_limit_error", "too many requests, slow down",
                             headers={"retry-after": str(wait)})
        if budget.exhausted():
            return api_error(403, "permission_error",
                             "the demo's daily budget is used up; try tomorrow or use your own key")

        try:
            message = await run_in_threadpool(
                upstream.messages.create, **upstream_params(payload, model, effort))
        except anthropic.APIStatusError as exc:
            log.warning("upstream status=%s", exc.status_code)
            if exc.status_code in (400, 429):  # caused by the request or by load: tell the client
                return api_error(exc.status_code, "invalid_request_error" if exc.status_code == 400
                                 else "rate_limit_error", "upstream rejected the request")
            # 401/403 (key or spend limit) and 5xx: don't reveal account details
            return api_error(503, "api_error", "service temporarily unavailable")
        except anthropic.APIConnectionError:
            log.warning("upstream connection error")
            return api_error(502, "api_error", "could not reach the model provider")

        cost = estimate_cost(message.model, message.usage)
        spent = budget.add(cost)
        u = message.usage
        # Metadata only: never message content (LGPD) and never IP addresses
        log.info("ok model=%s in=%s out=%s cache_read=%s cache_write=%s cost=%.5f today=%.4f",
                 message.model, u.input_tokens, u.output_tokens, u.cache_read_input_tokens,
                 u.cache_creation_input_tokens, cost, spent)
        return JSONResponse(message.to_dict())

    return app
