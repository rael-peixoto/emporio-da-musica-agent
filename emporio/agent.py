"""The agent loop: one customer message in, one reply out, with tool calls in between.

Plain Anthropic SDK and a hand-written loop (decision D10). The same code runs against the
Anthropic API directly or through the hosted proxy; only the client differs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

import anthropic

from emporio import config
from emporio.catalog import Catalog
from emporio.config import Settings
from emporio.llm import estimate_cost
from emporio.prompt import LANGUAGE_REMINDER, system_blocks
from emporio.tools import TOOLS, ToolBox

TOO_LONG = ("Sua mensagem ficou um pouco longa para mim. Pode resumir em até "
            f"{config.MAX_INPUT_CHARS} caracteres?")
SESSION_OVER = ("Esta conversa atingiu o limite de mensagens desta demonstração. "
                "Para continuar, é só iniciar uma nova conversa.")
REFUSED = ("Desculpe, não consigo ajudar com isso por aqui. Posso te ajudar com algo sobre "
           "nossos instrumentos ou pedidos?")
NO_TEXT = "Desculpe, não consegui formular uma resposta. Pode repetir a pergunta?"

# Function words that tell an English reply from a Portuguese one (product names don't count)
ENGLISH_WORDS = frozenset(
    "the and you we is are have for with your our can would any what yes it this that there "
    "they from if in to of be will".split())
PORTUGUESE_WORDS = frozenset(
    "de que não para com você em os as um uma temos está se por mais da do no na é o e ou "
    "também posso pode sim".split())


def looks_english(text: str) -> bool:
    words = re.findall(r"[a-zà-ú]+", text.lower())
    english = sum(w in ENGLISH_WORDS for w in words)
    portuguese = sum(w in PORTUGUESE_WORDS for w in words)
    return english >= 3 and english > portuguese


def reply_text(response) -> str:
    return "\n".join(b.text for b in response.content if b.type == "text").strip()


@dataclass
class ToolCall:
    name: str
    input: dict
    output: str
    is_error: bool


@dataclass
class Turn:
    user: str
    reply: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    cost_usd: float = 0.0
    api_calls: int = 0
    model: str = ""  # as reported by the API (the proxy may override the requested model)
    tokens: dict[str, int] = field(default_factory=lambda: dict.fromkeys(
        ("input", "output", "cache_read", "cache_write"), 0))


class Agent:
    def __init__(self, client: anthropic.Anthropic, settings: Settings, catalog: Catalog,
                 now: datetime, toolbox: ToolBox | None = None):
        self.client = client
        self.settings = settings
        self.now = now
        self.toolbox = toolbox or ToolBox(catalog, now)
        self.history: list[dict] = []
        self.turns = 0
        self.total_cost_usd = 0.0

    def send(self, text: str) -> Turn:
        text = text.strip()
        if len(text) > config.MAX_INPUT_CHARS:
            return Turn(text, TOO_LONG)
        if self.turns >= config.MAX_TURNS or self.total_cost_usd >= config.SESSION_BUDGET_USD:
            return Turn(text, SESSION_OVER)

        turn = Turn(text, "")
        checkpoint = len(self.history)
        self.history.append({"role": "user", "content": text})
        # Operator reminder right after the customer's words (mid-conversation system message).
        # Kept in the history: the API expects history to be append-only.
        self.history.append({"role": "system", "content": LANGUAGE_REMINDER})
        try:
            response = self._run_tool_loop(turn)
        except Exception:
            del self.history[checkpoint:]  # keep the history valid for the next message
            raise
        finally:
            self.total_cost_usd += turn.cost_usd

        if response.stop_reason == "refusal":
            self.history.append({"role": "assistant", "content": REFUSED})
            turn.reply = REFUSED
        else:
            content = response.content
            if response.stop_reason == "max_tokens":
                # A truncated tool call has no result; leaving it in would break the next request
                content = [b for b in content if b.type != "tool_use"]
            text_parts = [b.text for b in content if b.type == "text"]
            turn.reply = "\n".join(text_parts).strip() or NO_TEXT
            self.history.append({"role": "assistant", "content": content or turn.reply})
        self.turns += 1
        return turn

    def _run_tool_loop(self, turn: Turn):
        rounds, language_retries = 0, 1
        while True:
            last_round = rounds == config.MAX_TOOL_ROUNDS
            response = self._call(tool_choice={"type": "none"} if last_round else None)
            turn.api_calls += 1
            turn.model = response.model
            turn.cost_usd += estimate_cost(response.model, response.usage)
            usage = response.usage
            turn.tokens["input"] += usage.input_tokens
            turn.tokens["output"] += usage.output_tokens
            turn.tokens["cache_read"] += usage.cache_read_input_tokens or 0
            turn.tokens["cache_write"] += usage.cache_creation_input_tokens or 0
            if response.stop_reason != "tool_use":
                # Hard rule enforced in code: an English reply is resampled once. The discarded
                # reply never enters the history, so the history stays append-only.
                if language_retries and looks_english(reply_text(response)):
                    language_retries -= 1
                    continue
                return response
            rounds += 1
            self.history.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                output, is_error = self.toolbox.run(block.name, dict(block.input))
                turn.tool_calls.append(ToolCall(block.name, dict(block.input), output, is_error))
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": output, "is_error": is_error})
            self.history.append({"role": "user", "content": results})

    def _call(self, tool_choice: dict | None):
        params = {
            "model": self.settings.model,
            "max_tokens": config.MAX_TOKENS,
            "system": system_blocks(self.now),
            "tools": TOOLS,
            "messages": self.history,
            "output_config": {"effort": self.settings.effort},
        }
        if tool_choice:
            params["tool_choice"] = tool_choice
        return self.client.messages.create(**params)
