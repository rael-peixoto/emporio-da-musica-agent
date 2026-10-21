"""Tools the model can call: the only path from the LLM to the store data.

Outputs are JSON with values already formatted for the customer (R$, dd/mm/yyyy), so the
model never does arithmetic. No output ever contains a customer's e-mail, phone, full name
or address.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from emporio import rules
from emporio.catalog import Catalog, Order, Product
from emporio.config import LOGS_DIR

MAX_SEARCH_RESULTS = 20

CATEGORY_NAMES = [
    "Guitarras", "Baixos", "Baterias e Percussão", "Teclados e Pianos", "Violões",
    "Instrumentos de Sopro (Madeiras)", "Instrumentos de Sopro (Metais)",
    "Cordas Orquestrais", "Ukuleles",
]

TOOLS = [
    {
        "name": "buscar_produtos",
        "description": (
            "Busca instrumentos no catálogo da loja. Use para qualquer pergunta sobre quais "
            "produtos existem, faixas de preço ou disponibilidade. Os preços retornados já "
            "consideram promoções ativas. Por padrão retorna só produtos disponíveis para venda."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "termo": {"type": "string",
                          "description": "Marca, modelo ou característica, ex.: 'Takamine GD20', 'Yamaha', '7 cordas'."},
                "categoria": {"type": "string", "enum": CATEGORY_NAMES},
                "preco_min": {"type": "number", "description": "Preço mínimo em reais."},
                "preco_max": {"type": "number", "description": "Preço máximo em reais."},
                "cordas": {"type": "string", "enum": ["nylon", "aço"],
                           "description": "Tipo de cordas (violões e ukuleles)."},
                "eletrico": {"type": "boolean",
                             "description": "true para eletroacústicos (com captação), false para acústicos."},
                "incluir_indisponiveis": {"type": "boolean",
                                          "description": "Inclui itens sem estoque, descontinuados ou em breve."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "detalhes_produto",
        "description": (
            "Detalhes de um produto pelo id: especificações, disponibilidade, preço de tabela, "
            "promoção ativa, preço no PIX e parcelamento máximo sem juros. Use antes de informar "
            "preço, estoque ou condições de pagamento de um produto."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"produto_id": {"type": "integer"}},
            "required": ["produto_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "listar_categorias",
        "description": "Lista as categorias do catálogo com a quantidade de produtos disponíveis em cada uma.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "consultar_pedido",
        "description": (
            "Consulta status, itens, rastreio e datas de um pedido. Exige o número do pedido E o "
            "e-mail ou telefone cadastrado do cliente; peça os dois antes de chamar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "numero_pedido": {"type": "integer"},
                "email_ou_telefone": {"type": "string"},
            },
            "required": ["numero_pedido", "email_ou_telefone"],
            "additionalProperties": False,
        },
    },
    {
        "name": "registrar_atendimento_humano",
        "description": (
            "Registra um encaminhamento para a equipe humana (reclamações, dúvidas que o manual "
            "não resolve, pedidos com problema) e devolve um número de protocolo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "motivo": {"type": "string",
                           "enum": ["reclamação", "dúvida sobre política", "problema com pedido", "outro"]},
                "resumo": {"type": "string", "description": "Resumo curto do caso, sem dados sensíveis."},
                "contato": {"type": "string", "description": "Como o cliente prefere ser contatado, se informou."},
            },
            "required": ["motivo", "resumo"],
            "additionalProperties": False,
        },
    },
]

SPEC_LABELS = {
    "top": "tampo", "back_sides": "fundo e laterais", "neck": "braço", "strings": "cordas",
    "scale": "escala", "electronics": "eletrônica", "color": "cor", "body": "corpo",
    "shells": "cascos", "pieces": "peças", "hardware": "ferragens", "keys": "teclas",
    "type": "tipo", "polyphony": "polifonia",
}
ORDER_STATUS = {
    "pending": "pendente", "confirmed": "confirmado", "shipped": "enviado",
    "delivered": "entregue", "cancelled": "cancelado",
}
ORDER_NOT_FOUND = (
    "Não encontramos um pedido com esse número e esse e-mail/telefone. "
    "Peça ao cliente para conferir os dados."
)


def availability(product: Product) -> str:
    if product.sellable:
        return "disponível"
    if product.status == "discontinued":
        return "descontinuado (não faz mais parte do catálogo)"
    if product.status == "coming_soon":
        return "em breve (ainda não está à venda)"
    return "temporariamente indisponível (sem estoque)"


def promotion_text(product: Product) -> str | None:
    promo = product.promotion
    if promo is None:
        return None
    return (f"{promo.description}: {promo.discount_percent}% de desconto, de "
            f"{rules.format_brl(product.list_price)} por {rules.format_brl(product.price)}")


def installments_text(price: Decimal) -> str:
    n = rules.max_installments(price)
    if n == 1:
        return "somente à vista (o valor não atinge a parcela mínima)"
    return f"até {n}x sem juros de {rules.format_brl(price / n)}"


def payment_text(method: str) -> str:
    if method.startswith("credit_"):
        return f"cartão de crédito em {method.removeprefix('credit_')}"
    return {"pix": "PIX", "debit": "cartão de débito", "boleto": "boleto bancário"}.get(method, method)


class ToolBox:
    def __init__(self, catalog: Catalog, now: datetime, handoff_log: Path | None = None):
        self.catalog = catalog
        self.now = now
        self.handoff_log = handoff_log or LOGS_DIR / "handoffs.jsonl"

    def run(self, name: str, tool_input: dict) -> tuple[str, bool]:
        """Execute a tool; returns (JSON text, is_error)."""
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return json.dumps({"erro": f"ferramenta desconhecida: {name}"}), True
        try:
            result = handler(**tool_input)
        except (TypeError, ValueError, InvalidOperation) as exc:
            return json.dumps({"erro": f"parâmetros inválidos: {exc}"}, ensure_ascii=False), True
        return json.dumps(result, ensure_ascii=False), False

    def _tool_buscar_produtos(self, termo=None, categoria=None, preco_min=None, preco_max=None,
                              cordas=None, eletrico=None, incluir_indisponiveis=False):
        found = self.catalog.search(
            term=termo,
            category=categoria,
            min_price=None if preco_min is None else Decimal(str(preco_min)),
            max_price=None if preco_max is None else Decimal(str(preco_max)),
            strings=cordas,
            electric=eletrico,
            only_sellable=not incluir_indisponiveis,
        )
        products = []
        for p in found[:MAX_SEARCH_RESULTS]:
            item = {"id": p.id, "nome": p.name, "categoria": p.category.name,
                    "preco": rules.format_brl(p.price), "disponibilidade": availability(p)}
            if p.promotion:
                item["promocao"] = promotion_text(p)
            products.append(item)
        return {"total_encontrado": len(found), "produtos": products}

    def _tool_detalhes_produto(self, produto_id):
        product = self.catalog.products.get(int(produto_id))
        if product is None:
            return {"erro": f"produto {produto_id} não existe no catálogo"}
        details = {
            "id": product.id,
            "nome": product.name,
            "categoria": product.category.name,
            "descricao": product.description or "indisponível (use as especificações)",
            "especificacoes": {SPEC_LABELS.get(k, k): v for k, v in product.specs.items()},
            "disponibilidade": availability(product),
        }
        if product.sellable:
            details["unidades_em_estoque"] = product.stock
        details["preco_tabela"] = rules.format_brl(product.list_price)
        details["promocao_ativa"] = promotion_text(product)
        details["preco_final"] = rules.format_brl(product.price)
        if product.pix_price is None:
            details["preco_pix"] = "o desconto de 5% no PIX não se aplica sobre preço promocional"
        else:
            details["preco_pix"] = f"{rules.format_brl(product.pix_price)} (5% de desconto à vista)"
        details["parcelamento_cartao"] = installments_text(product.price)
        return details

    def _tool_listar_categorias(self):
        return [{"categoria": c.name, "descricao": c.description,
                 "produtos_disponiveis": self.catalog.available_count(c)}
                for c in self.catalog.categories.values()]

    def _tool_consultar_pedido(self, numero_pedido, email_ou_telefone):
        order = self.catalog.find_order(int(numero_pedido), str(email_ou_telefone))
        if order is None:
            return {"encontrado": False, "mensagem": ORDER_NOT_FOUND}
        return {"encontrado": True, **self._order_view(order)}

    def _order_view(self, order: Order) -> dict:
        today = self.now.date()
        view = {
            "numero": order.id,
            "primeiro_nome_cliente": order.customer.first_name,
            "status": ORDER_STATUS.get(order.status, order.status),
            "data_pedido": rules.format_date(order.order_date),
            "dias_desde_o_pedido": (today - order.order_date).days,
            "itens": [{"produto": i.product.name, "quantidade": i.quantity} for i in order.items],
            "total_pago": rules.format_brl(order.total),
            "forma_pagamento": payment_text(order.payment_method),
            "codigo_rastreio": order.tracking_code,
        }
        if order.estimated_delivery:
            view["previsao_entrega"] = rules.format_date(order.estimated_delivery)
            view["dias_desde_a_previsao_de_entrega"] = (today - order.estimated_delivery).days
            view["entrega_atrasada"] = (order.status in ("pending", "confirmed", "shipped")
                                        and order.estimated_delivery < today)
        if order.notes:
            view["observacoes"] = order.notes
        if order.status == "delivered" and order.estimated_delivery:
            view["prazos"] = self._deadlines(order, today)
        return view

    @staticmethod
    def _deadlines(order: Order, today) -> dict:
        """Policy deadlines (§4.1, §4.2, §8.1), computed here so the model never does date maths.

        The receipt date is not recorded, so the estimated delivery date stands in for it.
        """
        def deadline(start, days):
            end = start + timedelta(days=days)
            state = "dentro do prazo" if today <= end else "prazo encerrado"
            return f"{rules.format_date(end)} ({state})"

        received = order.estimated_delivery
        return {
            "base": "data de recebimento não registrada; usada a previsão de entrega",
            "devolucao_por_arrependimento_ate": deadline(received, 7),
            "troca_por_defeito_com_a_loja_ate": deadline(order.order_date, 30),
            "garantia_legal_ate": deadline(received, 90),
        }

    def _tool_registrar_atendimento_humano(self, motivo, resumo, contato=None):
        protocol = f"EM-{self.now:%Y%m%d}-{secrets.token_hex(2).upper()}"
        self.handoff_log.parent.mkdir(parents=True, exist_ok=True)
        record = {"protocolo": protocol, "registrado_em": self.now.isoformat(),
                  "motivo": motivo, "resumo": resumo, "contato": contato}
        with self.handoff_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        result = {"protocolo": protocol, "status": "encaminhado para a equipe"}
        if motivo == "reclamação":
            result["prazo_de_retorno"] = "até 24 horas úteis"
        return result
