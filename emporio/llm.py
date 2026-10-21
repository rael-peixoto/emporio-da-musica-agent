"""Anthropic client for both transports, and cost estimation from API usage."""

from __future__ import annotations

import urllib.request

import anthropic

from emporio.config import Settings

# USD per 1M tokens: input, output, cache read, cache write (5 min). Official pricing, 2026-10-21.
PRICES = {
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
    "claude-sonnet-5-5": (2.00, 10.00, 0.10, 2.50),
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
}
FALLBACK_PRICES = PRICES["claude-opus-5-5"]  # unknown model: assume the most expensive


def estimate_cost(model: str, usage) -> float:
    price_in, price_out, price_read, price_write = PRICES.get(model, FALLBACK_PRICES)
    tokens = (
        usage.input_tokens * price_in
        + usage.output_tokens * price_out
        + (usage.cache_read_input_tokens or 0) * price_read
        + (usage.cache_creation_input_tokens or 0) * price_write
    )
    return tokens / 1_000_000


def make_client(settings: Settings) -> anthropic.Anthropic:
    if settings.backend == "direct":
        return anthropic.Anthropic(timeout=60, max_retries=2)  # key read from the environment
    # Proxy mode: the access code travels in the API-key header and the proxy swaps in the
    # real key server-side. Passing it explicitly means a local ANTHROPIC_API_KEY is never sent.
    return anthropic.Anthropic(
        base_url=settings.proxy_url, api_key=settings.access_code, timeout=120, max_retries=2
    )


def wake_proxy(proxy_url: str, timeout: float = 90) -> bool:
    """Ping the proxy so a sleeping free-tier instance starts before the first chat message."""
    try:
        with urllib.request.urlopen(f"{proxy_url}/health", timeout=timeout) as response:
            return response.status == 200
    except OSError:
        return False
