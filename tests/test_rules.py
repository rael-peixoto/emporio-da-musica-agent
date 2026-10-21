"""Business rules from the policy manual. Expected values are worked out by hand from §2–§3."""

from datetime import datetime
from decimal import Decimal

import pytest

from emporio import rules
from emporio.config import STORE_TZ


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        ("40", 1),  # 2x would be R$ 20, below the R$ 50 minimum
        ("100", 2),  # 2x R$ 50 is exactly the minimum
        ("159.90", 3),  # 3x R$ 53,30; 4x would be R$ 39,98 < R$ 80
        ("349.90", 4),  # 4x R$ 87,48 >= R$ 80; 5x R$ 69,98 < R$ 80
        ("700", 7),  # 7x R$ 100 meets the 7-12x minimum; 8x R$ 87,50 does not
        ("1000", 10),
        ("2199", 12),
    ],
)
def test_max_installments_follows_section_3_1_tiers(price, expected):
    assert rules.max_installments(Decimal(price)) == expected


def test_apply_discount_rounds_to_cents():
    assert rules.apply_discount(Decimal("2199"), 5) == Decimal("2089.05")
    assert rules.apply_discount(Decimal("2399"), 18) == Decimal("1967.18")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1299", "R$ 1.299,00"),
        ("599.9", "R$ 599,90"),
        ("12000", "R$ 12.000,00"),
        ("2089.05", "R$ 2.089,05"),
        ("1234567.891", "R$ 1.234.567,89"),
    ],
)
def test_format_brl(value, expected):
    assert rules.format_brl(Decimal(value)) == expected


def at(day: int, hour: int, minute: int = 0) -> datetime:
    # October 2026: 21 is a Wednesday, 23 Friday, 24 Saturday, 25 Sunday, 26 Monday
    return datetime(2026, 10, day, hour, minute, tzinfo=STORE_TZ)


@pytest.mark.parametrize(
    ("moment", "open_", "next_open"),
    [
        (at(23, 17, 59), True, at(24, 9)),
        (at(23, 18, 0), False, at(24, 9)),
        (at(24, 12, 59), True, at(26, 9)),
        (at(24, 13, 0), False, at(26, 9)),
        (at(25, 10, 0), False, at(26, 9)),
        (at(26, 8, 59), False, at(26, 9)),
        (at(21, 10, 0), True, at(22, 9)),
    ],
)
def test_opening_hours(moment, open_, next_open):
    assert rules.is_open(moment) is open_
    assert rules.next_opening(moment) == next_open
