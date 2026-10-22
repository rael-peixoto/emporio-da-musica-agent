"""Data loading and queries. Expected values were checked by hand against data/*.csv."""

from decimal import Decimal

import pytest

from emporio.catalog import Catalog


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return Catalog.load()


def ids(products) -> list[int]:
    return [p.id for p in products]


def test_row_counts(catalog):
    assert catalog.row_counts() == {
        "categories": 9,
        "products": 65,
        "active_promotions": 4,
        "customers": 50,
        "orders": 20,
        "order_items": 22,
    }


@pytest.mark.parametrize(
    ("product_id", "sellable"),
    [
        (81, True),
        (96, False),  # active but out of stock
        (113, False),  # discontinued, no stock
        (130, False),  # coming_soon even though stock is 2
        (136, False),  # discontinued even though stock is 13
    ],
)
def test_sellable_requires_active_status_and_stock(catalog, product_id, sellable):
    assert catalog.products[product_id].sellable is sellable


def test_inconsistent_descriptions_are_withheld(catalog):
    assert catalog.products[142].description is None  # "Korg" described as a Roland
    assert catalog.products[138].description is not None  # StingRay is a Music Man model
    assert catalog.products[95].description is not None


def test_takamine_gd20_pricing(catalog):
    gd20 = catalog.products[95]
    assert gd20.promotion is None  # its 12% "Oferta Especial" is inactive
    assert gd20.price == Decimal("2199.00")
    assert gd20.pix_price == Decimal("2089.05")
    assert gd20.max_installments == 12


@pytest.mark.parametrize(
    ("product_id", "percent", "promo_price"),
    [(127, 10, "323.10"), (121, 20, "439.20"), (90, 18, "1967.18"), (94, 8, "5519.08")],
)
def test_active_promotions_set_price_and_disable_pix(catalog, product_id, percent, promo_price):
    product = catalog.products[product_id]
    assert product.promotion.discount_percent == percent
    assert product.price == Decimal(promo_price)
    assert product.pix_price is None  # PIX never stacks on a promotion (§6.2)


def test_installments_use_the_promotional_price(catalog):
    assert catalog.products[127].max_installments == 4  # 4x R$ 80,78 on R$ 323,10


def test_violoes_up_to_1000_briefing_question(catalog):
    result = catalog.search(category="Violões", max_price=Decimal("1000"))
    assert ids(result) == [83, 85, 89, 88, 81, 84, 87, 86, 107, 82, 91, 112]
    assert catalog.search(category="violoes", max_price=Decimal("1000")) == result


def test_search_can_include_unavailable_products(catalog):
    result = catalog.search(category="Violões", max_price=Decimal("1000"), only_sellable=False)
    assert {96, 113} <= set(ids(result))
    assert len(result) == 14


@pytest.mark.parametrize("term", ["takamine gd20", "Takamine GD-20", "takamini gd20"])
def test_term_search_tolerates_case_punctuation_and_typos(catalog, term):
    assert ids(catalog.search(term=term)) == [95]


@pytest.mark.parametrize("term", ["baixo elétrico", "contrabaixo", "contrabaixos elétricos"])
def test_portuguese_terms_find_basses_named_in_english(catalog, term):
    # 135 and 137 are named "... Electric Bass"; their (withheld) descriptions were the only
    # Portuguese text, so without synonyms only 138 was found
    assert ids(catalog.search(term=term)) == [138, 135, 137]


@pytest.mark.parametrize("term", ["SN-7C 7 cordas nylon", "cordas nylon SN-7C", "Shelby SN-7C"])
def test_model_code_is_not_matched_across_word_boundaries(catalog, term):
    # "sn" used to match inside "corda|s n|ylon" and "7c" inside "7|c|ordas", so other 7-string
    # violões looked like matches and the discontinued SN-7C (113) was never shown
    assert ids(catalog.search(term=term)) == []
    assert ids(catalog.search(term=term, only_sellable=False)) == [113]


def test_electric_guitar_search_is_unchanged(catalog):
    assert sorted(ids(catalog.search(term="guitarra elétrica"))) == [131, 132, 133, 134, 145]


def test_filters_by_string_type_and_electronics(catalog):
    result = catalog.search(category="Violões", strings="nylon", electric=True)
    assert ids(result) == [101, 99, 111, 115, 100, 98, 102]


@pytest.mark.parametrize(("kwargs"), [{"category": "Sintetizadores"}, {"strings": "seda"}])
def test_unknown_filters_match_nothing(catalog, kwargs):
    assert catalog.search(**kwargs) == []


def test_available_counts_per_category(catalog):
    counts = {c.name: catalog.available_count(c) for c in catalog.categories.values()}
    assert counts["Violões"] == 33
    assert counts["Ukuleles"] == 14
    assert counts["Instrumentos de Sopro (Madeiras)"] == 0
    assert counts["Instrumentos de Sopro (Metais)"] == 0
    assert counts["Cordas Orquestrais"] == 0
    assert sum(counts.values()) == 61


@pytest.mark.parametrize(
    "identifier",
    ["pedro.oliveira@jmail.com", " PEDRO.OLIVEIRA@jmail.com ", "(67) 98432-1098",
     "+55 67 98432-1098", "984321098"],
)
def test_find_order_accepts_customer_email_or_phone(catalog, identifier):
    order = catalog.find_order(1, identifier)
    assert order is not None
    assert order.customer.first_name == "Pedro"
    assert order.total == Decimal("11499.00")
    assert order.tracking_code == "BRAB1234567BR"


@pytest.mark.parametrize(
    ("order_id", "identifier"),
    [
        (1, "lucas.mendes@jmail.com"),  # another customer's e-mail
        (1, "1098"),  # too few digits to identify anyone
        (1, ""),
        (999, "pedro.oliveira@jmail.com"),  # order does not exist
    ],
)
def test_find_order_rejects_unverified_requests(catalog, order_id, identifier):
    assert catalog.find_order(order_id, identifier) is None


def test_orders_are_reported_as_recorded(catalog):
    order = catalog.find_order(3, "isabela.moreira@jmail.com")
    assert order.total == Decimal("3450.00")  # items add up to 3,498; not "corrected"
    assert [(i.product.id, i.quantity) for i in order.items] == [(130, 2)]
