"""Transport selection. Tests never load the real .env, so they never touch a real key."""

import pytest

from emporio.config import load_settings
from emporio.llm import estimate_cost, make_client

ENV_VARS = ("ANTHROPIC_API_KEY", "LLM_BACKEND", "EMPORIO_ACCESS_CODE", "PROXY_URL", "MODEL", "EFFORT")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def settings(monkeypatch, **env):
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return load_settings(env_file=None)


def test_own_key_selects_direct_mode(monkeypatch):
    assert settings(monkeypatch, ANTHROPIC_API_KEY="test-key").backend == "direct"


def test_no_key_selects_proxy_mode(monkeypatch):
    s = settings(monkeypatch, EMPORIO_ACCESS_CODE="code-123", PROXY_URL="https://proxy.test/")
    assert (s.backend, s.proxy_url, s.access_code) == ("proxy", "https://proxy.test", "code-123")


def test_proxy_mode_without_access_code_explains_both_options(monkeypatch):
    with pytest.raises(ValueError, match="EMPORIO_ACCESS_CODE.*ANTHROPIC_API_KEY"):
        settings(monkeypatch, PROXY_URL="https://proxy.test")


@pytest.mark.parametrize(
    "env",
    [{"LLM_BACKEND": "direct"}, {"LLM_BACKEND": "cloud", "ANTHROPIC_API_KEY": "k"},
     {"ANTHROPIC_API_KEY": "k", "EFFORT": "turbo"}],
)
def test_invalid_configurations_are_rejected(monkeypatch, env):
    with pytest.raises(ValueError):
        settings(monkeypatch, **env)


def test_proxy_client_never_sends_the_local_key(monkeypatch):
    s = settings(monkeypatch, ANTHROPIC_API_KEY="my-real-key", LLM_BACKEND="proxy",
                 EMPORIO_ACCESS_CODE="code-123", PROXY_URL="https://proxy.test")
    client = make_client(s)
    assert client.api_key == "code-123"
    assert str(client.base_url).startswith("https://proxy.test")


class Usage:
    def __init__(self, i, o, read=0, write=0):
        self.input_tokens, self.output_tokens = i, o
        self.cache_read_input_tokens, self.cache_creation_input_tokens = read, write


def test_cost_estimate_uses_official_haiku_prices():
    # 1M of each token type: 0.10 + 0.50 + 0.01 + 0.125
    usage = Usage(1_000_000, 1_000_000, 1_000_000, 1_000_000)
    assert estimate_cost("claude-haiku-5-5", usage) == pytest.approx(0.735)


def test_unknown_model_is_priced_conservatively():
    assert estimate_cost("some-new-model", Usage(1_000_000, 0)) == pytest.approx(4.00)
