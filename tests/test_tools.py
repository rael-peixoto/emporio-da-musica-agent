"""Tool outputs: exact customer-facing values and the personal-data boundary."""

import json
from datetime import datetime

import pytest

from emporio.catalog import Catalog
from emporio.config import STORE_TZ
from emporio.tools import CATEGORY_NAMES, TOOLS, ToolBox

NOW = datetime(2026, 3, 25, 10, 0, tzinfo=STORE_TZ)


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return Catalog.load()


@pytest.fixture
def toolbox(catalog, tmp_path) -> ToolBox:
    return ToolBox(catalog, NOW, handoff_log=tmp_path / "handoffs.jsonl")


def call(toolbox, name, **kwargs):
    output, is_error = toolbox.run(name, kwargs)
    assert not is_error, output
    return json.loads(output)


def test_category_enum_matches_the_data(catalog):
    assert CATEGORY_NAMES == [c.name for c in catalog.categories.values()]


def test_every_tool_has_a_handler(toolbox):
    for tool in TOOLS:
        assert callable(getattr(toolbox, f"_tool_{tool['name']}"))


def test_search_violoes_up_to_1000(toolbox):
    result = call(toolbox, "buscar_produtos", categoria="Violões", preco_max=1000)
    assert result["total_encontrado"] == 12
    assert result["produtos"][0] == {
        "id": 83, "nome": "Tagima Memphis AC-39 Nylon Natural", "categoria": "Violões",
        "preco": "R$ 429,90", "disponibilidade": "disponível",
    }


@pytest.mark.parametrize(
    ("term", "product_id", "label"),
    [("Giannini GF-3D", 96, "temporariamente indisponível"), ("Shelby SN-7C", 113, "descontinuado")],
)
def test_named_unavailable_product_is_reported_not_hidden(toolbox, term, product_id, label):
    result = call(toolbox, "buscar_produtos", termo=term)
    assert [p["id"] for p in result["produtos"]] == [product_id]
    assert result["produtos"][0]["disponibilidade"].startswith(label)
    assert "não estão disponíveis" in result["observacao"]


def test_available_matches_need_no_fallback(toolbox):
    result = call(toolbox, "buscar_produtos", termo="Takamine GD20")
    assert "observacao" not in result


def test_takamine_gd20_details(toolbox):
    details = call(toolbox, "detalhes_produto", produto_id=95)
    assert details["preco_final"] == "R$ 2.199,00"
    assert details["preco_pix"] == "R$ 2.089,05 (5% de desconto à vista)"
    assert details["parcelamento_cartao"] == "até 12x sem juros de R$ 183,25"
    assert details["promocao_ativa"] is None


def test_promotion_shows_original_price_percent_and_promo_price(toolbox):
    details = call(toolbox, "detalhes_produto", produto_id=94)
    assert details["promocao_ativa"] == (
        "Desconto Exclusivo: 8% de desconto, de R$ 5.999,00 por R$ 5.519,08"
    )
    assert details["preco_final"] == "R$ 5.519,08"
    assert "não se aplica" in details["preco_pix"]


@pytest.mark.parametrize(
    ("product_id", "label"),
    [(96, "temporariamente indisponível"), (136, "descontinuado"), (130, "em breve")],
)
def test_unavailable_products_are_labelled_without_stock(toolbox, product_id, label):
    details = call(toolbox, "detalhes_produto", produto_id=product_id)
    assert details["disponibilidade"].startswith(label)
    assert "unidades_em_estoque" not in details


def test_contradictory_description_is_withheld(toolbox):
    assert call(toolbox, "detalhes_produto", produto_id=142)["descricao"].startswith("indisponível")


def test_empty_categories_report_zero(toolbox):
    counts = {c["categoria"]: c["produtos_disponiveis"] for c in call(toolbox, "listar_categorias")}
    assert counts["Cordas Orquestrais"] == 0
    assert counts["Violões"] == 33


def test_verified_order_lookup(toolbox):
    order = call(toolbox, "consultar_pedido", numero_pedido=8,
                 email_ou_telefone="anacarol.ferreira@coldmail.com")
    assert order["primeiro_nome_cliente"] == "Ana"
    assert order["status"] == "enviado"
    assert order["itens"] == [{"produto": "Kala KA-C Concert Mogno", "quantidade": 1}]
    assert order["total_pago"] == "R$ 349,90"
    assert order["forma_pagamento"] == "cartão de débito"
    assert order["codigo_rastreio"] == "BRJL5544332BR"
    assert order["previsao_entrega"] == "28/02/2026"
    assert order["dias_desde_a_previsao_de_entrega"] == 25  # 28/02 -> 25/03
    assert order["entrega_atrasada"] is True


def test_shipped_order_has_no_return_deadlines(toolbox):
    order = call(toolbox, "consultar_pedido", numero_pedido=8,
                 email_ou_telefone="anacarol.ferreira@coldmail.com")
    assert "prazos" not in order  # not received yet


def test_delivered_order_deadlines_are_computed(catalog, tmp_path):
    # Order 7: bought 03/02/2026, estimated delivery 17/02/2026; "today" = 20/02/2026
    toolbox = ToolBox(catalog, datetime(2026, 2, 20, 10, 0, tzinfo=STORE_TZ), tmp_path / "h.jsonl")
    order = call(toolbox, "consultar_pedido", numero_pedido=7,
                 email_ou_telefone="leticia.rocha@jmail.com")
    assert order["prazos"]["devolucao_por_arrependimento_ate"] == "24/02/2026 (dentro do prazo)"
    assert order["prazos"]["troca_por_defeito_com_a_loja_ate"] == "05/03/2026 (dentro do prazo)"
    assert order["prazos"]["garantia_legal_ate"] == "18/05/2026 (dentro do prazo)"


def test_expired_deadlines_are_marked(toolbox):
    # "today" = 25/03/2026: order 1 delivered around 25/10/2025
    order = call(toolbox, "consultar_pedido", numero_pedido=1,
                 email_ou_telefone="pedro.oliveira@jmail.com")
    assert order["prazos"]["devolucao_por_arrependimento_ate"] == "01/11/2025 (prazo encerrado)"


def test_unknown_order_and_wrong_identifier_look_the_same(toolbox):
    unknown = toolbox.run("consultar_pedido", {"numero_pedido": 999, "email_ou_telefone": "a@b.com"})
    mismatch = toolbox.run("consultar_pedido",
                           {"numero_pedido": 8, "email_ou_telefone": "lucas.mendes@jmail.com"})
    assert unknown == mismatch


def test_no_tool_output_leaks_customer_contact_data(catalog, toolbox):
    outputs = [
        toolbox.run("consultar_pedido",
                    {"numero_pedido": order.id, "email_ou_telefone": order.customer.email})[0]
        for order in catalog._orders.values()
    ]
    outputs += [toolbox.run(name, {})[0] for name in ("buscar_produtos", "listar_categorias")]
    blob = "\n".join(outputs)
    for customer in catalog._customers.values():
        assert customer.email not in blob
        assert customer.phone not in blob
        assert customer.name not in blob


def test_handoff_returns_protocol_and_logs_it(toolbox):
    result = call(toolbox, "registrar_atendimento_humano", motivo="reclamação",
                  resumo="Instrumento chegou com a caixa amassada")
    assert result["protocolo"].startswith("EM-20260325-")
    assert result["prazo_de_retorno"] == "até 24 horas úteis"
    logged = json.loads(toolbox.handoff_log.read_text(encoding="utf-8"))
    assert logged["protocolo"] == result["protocolo"]


@pytest.mark.parametrize(
    ("name", "tool_input"),
    [("detalhes_produto", {"produto_id": "abc"}), ("nao_existe", {}),
     ("buscar_produtos", {"inventado": 1})],
)
def test_bad_tool_calls_return_errors_instead_of_raising(toolbox, name, tool_input):
    output, is_error = toolbox.run(name, tool_input)
    assert is_error
    assert "erro" in json.loads(output)
