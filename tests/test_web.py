"""Local web UI, with a scripted fake model client: no network, no cost."""

from datetime import datetime
from types import SimpleNamespace as NS

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from emporio.agent import Agent
from emporio.catalog import Catalog
from emporio.config import STORE_TZ, Settings
from emporio.web import create_app

TOKEN = "page-token-for-tests"
NOW = datetime(2026, 3, 25, 10, 0, tzinfo=STORE_TZ)
SETTINGS = Settings("claude-haiku-5-5", "low", "direct", "", None)


def usage():
    return NS(input_tokens=1000, output_tokens=100, cache_read_input_tokens=0,
              cache_creation_input_tokens=0)


def text(reply):
    return NS(content=[NS(type="text", text=reply)], stop_reason="end_turn",
              model="claude-haiku-5-5", usage=usage())


def tool_use(name, tool_input):
    return NS(content=[NS(type="tool_use", name=name, input=tool_input, id="t1")],
              stop_reason="tool_use", model="claude-haiku-5-5", usage=usage())


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.messages = self

    def create(self, **params):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(scope="module")
def catalog():
    return Catalog.load()


def make(catalog, *responses):
    client = FakeClient(*responses)
    app = create_app(lambda: Agent(client, SETTINGS, catalog, NOW), SETTINGS, simulated=True,
                     token=TOKEN)
    return TestClient(app)


def post(client, path, body, token=TOKEN):
    return client.post(path, json=body, headers={"X-Page-Token": token})


def test_page_is_served_with_the_launch_token(catalog):
    page = make(catalog).get("/").text
    assert TOKEN in page
    assert "Empório da Música" in page


@pytest.mark.parametrize("token", ["", "wrong-token"])
def test_api_calls_without_the_page_token_are_refused(catalog, token):
    client = make(catalog)
    assert post(client, "/api/session", {}, token=token).status_code == 403


def test_chat_round_trip_exposes_tool_calls_for_the_console(catalog):
    client = make(catalog, tool_use("detalhes_produto", {"produto_id": 95}),
                  text("O Takamine GD20 sai por R$ 2.199,00."))
    session = post(client, "/api/session", {}).json()
    assert session["mode"] == "direct" and session["simulated"] is True
    assert session["now"] == "25/03/2026 10:00"

    turn = post(client, "/api/chat", {"session_id": session["session_id"],
                                      "message": "Quanto custa o Takamine GD20?"}).json()
    assert turn["reply"] == "O Takamine GD20 sai por R$ 2.199,00."
    assert turn["tool_calls"][0]["name"] == "detalhes_produto"
    assert '"preco_final": "R$ 2.199,00"' in turn["tool_calls"][0]["output"]
    assert turn["api_calls"] == 2 and turn["session_cost_usd"] > 0

    history = client.get("/api/history", params={"session_id": session["session_id"]},
                         headers={"X-Page-Token": TOKEN}).json()
    assert [t["reply"] for t in history["turns"]] == [turn["reply"]]


def test_unknown_session_is_404(catalog):
    client = make(catalog)
    assert post(client, "/api/chat", {"session_id": "nope", "message": "Oi"}).status_code == 404


def test_api_errors_become_friendly_messages(catalog):
    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://proxy.test"))
    client = make(catalog, error)
    session_id = post(client, "/api/session", {}).json()["session_id"]
    response = post(client, "/api/chat", {"session_id": session_id, "message": "Oi"})
    assert response.status_code == 502
    assert response.json()["error"].startswith("Não consegui conectar")


def test_api_docs_are_not_exposed(catalog):
    assert make(catalog).get("/docs").status_code == 404
