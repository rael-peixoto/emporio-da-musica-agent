"""Agent loop with a scripted fake client: no network, no cost."""

from datetime import datetime
from types import SimpleNamespace as NS

import pytest

from emporio import agent as agent_module
from emporio.agent import REFUSED, SESSION_OVER, TOO_LONG, Agent
from emporio.catalog import Catalog
from emporio.config import MAX_TOOL_ROUNDS, SESSION_BUDGET_USD, STORE_TZ, Settings
from emporio.tools import ToolBox

SETTINGS = Settings("claude-haiku-5-5", "low", "direct", "", None)
NOW = datetime(2026, 3, 25, 10, 0, tzinfo=STORE_TZ)


def usage():
    return NS(input_tokens=1000, output_tokens=100, cache_read_input_tokens=0,
              cache_creation_input_tokens=0)


def text(reply, stop="end_turn"):
    return NS(content=[NS(type="text", text=reply)], stop_reason=stop,
              model="claude-haiku-5-5", usage=usage())


def tool_use(name, tool_input, block_id="tool_1"):
    return NS(content=[NS(type="tool_use", name=name, input=tool_input, id=block_id)],
              stop_reason="tool_use", model="claude-haiku-5-5", usage=usage())


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.messages = self

    def create(self, **params):
        self.calls.append({**params, "messages": list(params["messages"])})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(scope="module")
def catalog():
    return Catalog.load()


def make_agent(catalog, tmp_path, *responses):
    client = FakeClient(*responses)
    toolbox = ToolBox(catalog, NOW, handoff_log=tmp_path / "h.jsonl")
    return Agent(client, SETTINGS, catalog, NOW, toolbox), client


def test_runs_tools_and_returns_the_final_text(catalog, tmp_path):
    agent, client = make_agent(catalog, tmp_path,
                               tool_use("detalhes_produto", {"produto_id": 95}),
                               text("O Takamine GD20 sai por R$ 2.199,00."))
    turn = agent.send("Quanto custa o Takamine GD20?")
    assert turn.reply == "O Takamine GD20 sai por R$ 2.199,00."
    assert [c.name for c in turn.tool_calls] == ["detalhes_produto"]
    assert '"preco_final": "R$ 2.199,00"' in turn.tool_calls[0].output
    second_request = client.calls[1]["messages"]
    assert second_request[-1]["content"][0]["type"] == "tool_result"
    assert [m["role"] for m in agent.history] == ["user", "assistant", "user", "assistant"]
    assert turn.api_calls == 2 and turn.cost_usd > 0


def test_requests_carry_cached_prompt_tools_and_limits(catalog, tmp_path):
    agent, client = make_agent(catalog, tmp_path, text("Olá!"))
    agent.send("Oi")
    request = client.calls[0]
    assert request["model"] == "claude-haiku-5-5"
    assert request["output_config"] == {"effort": "low"}
    assert request["max_tokens"] == agent_module.config.MAX_TOKENS
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert {t["name"] for t in request["tools"]} >= {"buscar_produtos", "consultar_pedido"}
    assert "tool_choice" not in request


def test_last_round_forbids_tools_so_the_model_must_answer(catalog, tmp_path):
    loops = [tool_use("listar_categorias", {}, f"t{i}") for i in range(MAX_TOOL_ROUNDS)]
    agent, client = make_agent(catalog, tmp_path, *loops, text("Resposta final"))
    turn = agent.send("Quais categorias?")
    assert turn.reply == "Resposta final"
    assert len(client.calls) == MAX_TOOL_ROUNDS + 1
    assert client.calls[-1]["tool_choice"] == {"type": "none"}
    assert all("tool_choice" not in c for c in client.calls[:-1])


def test_overlong_message_is_rejected_without_calling_the_api(catalog, tmp_path):
    agent, client = make_agent(catalog, tmp_path)
    assert agent.send("a" * 5000).reply == TOO_LONG
    assert client.calls == []


def test_session_budget_stops_the_conversation(catalog, tmp_path):
    agent, client = make_agent(catalog, tmp_path)
    agent.total_cost_usd = SESSION_BUDGET_USD
    assert agent.send("Oi").reply == SESSION_OVER
    assert client.calls == []


def test_refusal_gets_a_polite_reply_and_valid_history(catalog, tmp_path):
    agent, _ = make_agent(catalog, tmp_path, NS(content=[], stop_reason="refusal",
                                                model="claude-haiku-5-5", usage=usage()))
    assert agent.send("...").reply == REFUSED
    assert agent.history[-1] == {"role": "assistant", "content": REFUSED}


def test_truncated_tool_call_is_dropped_from_history(catalog, tmp_path):
    cut = NS(content=[NS(type="text", text="Vou verificar"),
                      NS(type="tool_use", name="listar_categorias", input={}, id="t1")],
             stop_reason="max_tokens", model="claude-haiku-5-5", usage=usage())
    agent, _ = make_agent(catalog, tmp_path, cut)
    agent.send("Quais categorias?")
    assert [b.type for b in agent.history[-1]["content"]] == ["text"]


def test_api_failure_leaves_history_unchanged(catalog, tmp_path):
    agent, _ = make_agent(catalog, tmp_path, RuntimeError("network down"))
    with pytest.raises(RuntimeError):
        agent.send("Oi")
    assert agent.history == []
