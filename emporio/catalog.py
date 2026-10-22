"""Case data: loading, cleaning and queries over the CSV files in data/.

Customer records are personal data (LGPD). They are reachable only through
`Catalog.find_order`, which requires the order number plus that order's
customer e-mail or phone.
"""

from __future__ import annotations

import csv
import difflib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from emporio import rules
from emporio.config import DATA_DIR

FILE_PREFIX = "desafio_tecnico_ai_eng - "

# Descriptions that name another brand or contradict the specs (e.g. 142 is a "Korg" described
# as an 88-key Roland while its spec says 61 keys). Name, price, stock and specs are treated as
# authoritative and these descriptions are withheld.
INCONSISTENT_DESCRIPTIONS = frozenset({135, 136, 137, 139, 140, 142, 144})

STRING_TYPES = {"nylon": "nylon", "aco": "steel", "steel": "steel"}

# Some product names are in English ("Music Man Bass 1X Electric Bass") while customers write in
# Portuguese, so a query word also matches its English form (accent-free, as normalize() leaves it).
SEARCH_SYNONYMS = {
    "baixo": "bass", "baixos": "bass", "contrabaixo": "bass", "contrabaixos": "bass",
    "eletrico": "electric", "eletrica": "electric", "eletricos": "electric", "eletricas": "electric",
}

MIN_PHONE_DIGITS = 8


def normalize(text: str) -> str:
    """Lowercase and strip accents, so "Violão" matches "violao"."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize(text))


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    description: str


@dataclass(frozen=True)
class Promotion:
    id: int
    product_id: int
    discount_percent: int
    description: str


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    category: Category
    list_price: Decimal
    description: str | None
    stock: int
    status: str  # active | discontinued | coming_soon
    specs: dict[str, str]
    promotion: Promotion | None  # best active promotion, if any

    @property
    def sellable(self) -> bool:
        return self.status == "active" and self.stock > 0

    @property
    def price(self) -> Decimal:
        """What the customer pays: the promotional price when a promotion is active."""
        if self.promotion:
            return rules.apply_discount(self.list_price, self.promotion.discount_percent)
        return self.list_price

    @property
    def pix_price(self) -> Decimal | None:
        """PIX discount on the list price; never stacked on a promotion (§6.2)."""
        if self.promotion:
            return None
        return rules.apply_discount(self.list_price, rules.PIX_DISCOUNT_PERCENT)

    @property
    def max_installments(self) -> int:
        return rules.max_installments(self.price)


@dataclass(frozen=True)
class Customer:
    id: int
    name: str
    phone: str
    email: str
    city: str

    @property
    def first_name(self) -> str:
        return self.name.split()[0]


@dataclass(frozen=True)
class OrderItem:
    product: Product
    quantity: int


@dataclass(frozen=True)
class Order:
    id: int
    customer: Customer
    order_date: date
    status: str  # pending | confirmed | shipped | delivered | cancelled
    total: Decimal
    payment_method: str
    tracking_code: str | None
    estimated_delivery: date | None
    notes: str | None
    items: tuple[OrderItem, ...]


class Catalog:
    def __init__(
        self,
        categories: dict[int, Category],
        products: dict[int, Product],
        promotions: list[Promotion],
        customers: dict[int, Customer],
        orders: dict[int, Order],
    ):
        self.categories = categories
        self.products = products
        self.promotions = promotions
        self._customers = customers
        self._orders = orders

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> Catalog:
        def rows(name: str) -> list[dict[str, str]]:
            with (data_dir / f"{FILE_PREFIX}{name}.csv").open(encoding="utf-8", newline="") as f:
                return list(csv.DictReader(f))

        categories = {
            int(r["category_id"]): Category(int(r["category_id"]), r["name"], r["description"])
            for r in rows("categories")
        }
        promotions = [
            Promotion(int(r["promotion_id"]), int(r["product_id"]), int(r["discount_percent"]),
                      r["description"])
            for r in rows("promotions")
            if r["is_active"] == "1"
        ]
        best_promotion: dict[int, Promotion] = {}
        for promo in promotions:  # promotions don't stack: keep the largest discount
            current = best_promotion.get(promo.product_id)
            if current is None or promo.discount_percent > current.discount_percent:
                best_promotion[promo.product_id] = promo

        products = {}
        for r in rows("products"):
            pid = int(r["product_id"])
            products[pid] = Product(
                id=pid,
                name=r["name"],
                category=categories[int(r["category_id"])],
                list_price=rules.money(r["price_brl"]),
                description=None if pid in INCONSISTENT_DESCRIPTIONS else r["description"],
                stock=int(r["stock_quantity"]),
                status=r["status"],
                specs={k: str(v) for k, v in json.loads(r["specs"]).items()},
                promotion=best_promotion.get(pid),
            )

        customers = {
            int(r["customer_id"]): Customer(int(r["customer_id"]), r["name"], r["phone"],
                                            r["email"], r["city"])
            for r in rows("customers")
        }
        items: dict[int, list[OrderItem]] = {}
        for r in rows("order_items"):
            items.setdefault(int(r["order_id"]), []).append(
                OrderItem(products[int(r["product_id"])], int(r["quantity"]))
            )
        orders = {}
        for r in rows("orders"):
            oid = int(r["order_id"])
            orders[oid] = Order(
                id=oid,
                customer=customers[int(r["customer_id"])],
                order_date=date.fromisoformat(r["order_date"]),
                status=r["status"],
                total=rules.money(r["total_brl"]),
                payment_method=r["payment_method"],
                tracking_code=r["tracking_code"] or None,
                estimated_delivery=(date.fromisoformat(r["estimated_delivery"])
                                    if r["estimated_delivery"] else None),
                notes=r["notes"] or None,
                items=tuple(items.get(oid, ())),
            )
        return cls(categories, products, promotions, customers, orders)

    def row_counts(self) -> dict[str, int]:
        return {
            "categories": len(self.categories),
            "products": len(self.products),
            "active_promotions": len(self.promotions),
            "customers": len(self._customers),
            "orders": len(self._orders),
            "order_items": sum(len(o.items) for o in self._orders.values()),
        }

    def category_by_name(self, name: str) -> Category | None:
        wanted = normalize(name).strip()
        return next((c for c in self.categories.values() if normalize(c.name) == wanted), None)

    def available_count(self, category: Category) -> int:
        return sum(1 for p in self.products.values() if p.category == category and p.sellable)

    def search(
        self,
        term: str | None = None,
        category: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        strings: str | None = None,
        electric: bool | None = None,
        only_sellable: bool = True,
    ) -> list[Product]:
        """Filter products; prices compare against what the customer pays (promo-aware).

        Results are sorted by price. An unknown category or string type matches nothing.
        """
        candidates = list(self.products.values())
        if category:
            cat = self.category_by_name(category)
            candidates = [p for p in candidates if p.category == cat]
        if strings:
            wanted = STRING_TYPES.get(normalize(strings))
            candidates = [p for p in candidates if wanted and p.specs.get("strings") == wanted]
        if electric is not None:
            flag = "yes" if electric else "no"
            candidates = [p for p in candidates if p.specs.get("electronics") == flag]
        if only_sellable:
            candidates = [p for p in candidates if p.sellable]
        if min_price is not None:
            candidates = [p for p in candidates if p.price >= min_price]
        if max_price is not None:
            candidates = [p for p in candidates if p.price <= max_price]
        if term:
            matched = [p for p in candidates if _matches(term, p, fuzzy=False)]
            # Fall back to typo-tolerant matching only when the exact match finds nothing
            candidates = matched or [p for p in candidates if _matches(term, p, fuzzy=True)]
        return sorted(candidates, key=lambda p: (p.price, p.id))

    def find_order(self, order_id: int, identifier: str) -> Order | None:
        """Return the order only if `identifier` is its customer's e-mail or phone.

        Unknown orders and mismatched identifiers both return None, so callers cannot tell
        which order numbers exist.
        """
        order = self._orders.get(order_id)
        if order is None or not _identifies(order.customer, identifier):
            return None
        return order


MIN_CROSS_WORD_TOKEN = 4


def _matches(term: str, product: Product, fuzzy: bool) -> bool:
    text = " ".join([product.name, product.category.name, product.description or "",
                     *product.specs.values()])
    words = _words(text)
    squashed = "".join(words)  # lets "GD20" match "GD-20"
    for token in _words(term):
        if any(token in word for word in words):
            continue
        # Only longer tokens may span word boundaries: a short one like "sn" would otherwise
        # match inside "corda|s n|ylon" and hide the product actually asked for (SN-7C)
        if len(token) >= MIN_CROSS_WORD_TOKEN and token in squashed:
            continue
        # Synonyms match whole words only: "bass" must not match a "Basswood" body
        if SEARCH_SYNONYMS.get(token) in words:
            continue
        if fuzzy and difflib.get_close_matches(token, words, n=1, cutoff=0.8):
            continue
        return False
    return True


def _identifies(customer: Customer, identifier: str) -> bool:
    identifier = identifier.strip()
    if "@" in identifier:
        return identifier.lower() == customer.email.lower()
    given = re.sub(r"\D", "", identifier)
    known = re.sub(r"\D", "", customer.phone)
    if len(given) < MIN_PHONE_DIGITS:
        return False
    # Accept with or without country/area code: +55 67 99812-3456, 67998123456, 998123456
    return known.endswith(given) or given.endswith(known)
