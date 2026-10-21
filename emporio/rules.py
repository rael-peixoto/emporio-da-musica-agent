"""Store business rules from the policy manual, as pure functions.

Money uses Decimal so prices, discounts and installments are exact.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")

# §3: PIX gets 5% off the list price; §6.2: never on top of a promotional price.
PIX_DISCOUNT_PERCENT = 5

# §3.1: (max installments in the tier, minimum installment value). The table in §3 says
# "minimum R$ 100" but §3.1 is more specific, so it prevails. For up to 3x the manual says
# "no minimum (except below R$ 50,00)", read here as a R$ 50 minimum installment.
INSTALLMENT_TIERS = ((3, Decimal("50")), (6, Decimal("80")), (12, Decimal("100")))
MAX_INSTALLMENTS = 12

# §2: weekday -> (opening hour, closing hour). Sunday (6) is closed; holidays are not
# listed in the manual, so they are not modelled.
OPENING_HOURS = {0: (9, 18), 1: (9, 18), 2: (9, 18), 3: (9, 18), 4: (9, 18), 5: (9, 13)}


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def apply_discount(price: Decimal, percent: int) -> Decimal:
    return money(price * (100 - percent) / 100)


def min_installment_value(installments: int) -> Decimal:
    for max_n, minimum in INSTALLMENT_TIERS:
        if installments <= max_n:
            return minimum
    raise ValueError(f"at most {MAX_INSTALLMENTS} installments")


def max_installments(price: Decimal) -> int:
    """Largest interest-free installment count whose value meets its tier minimum (§3.1)."""
    best = 1  # paying in full is always allowed
    for n in range(2, MAX_INSTALLMENTS + 1):
        if price / n >= min_installment_value(n):
            best = n
    return best


def format_brl(value: Decimal) -> str:
    """Format as Brazilian currency, e.g. R$ 1.299,00."""
    text = f"{money(value):,.2f}"  # 1,299.00
    return "R$ " + text.replace(",", "_").replace(".", ",").replace("_", ".")


def format_date(value: date) -> str:
    return value.strftime("%d/%m/%Y")


def is_open(now: datetime) -> bool:
    hours = OPENING_HOURS.get(now.weekday())
    return hours is not None and hours[0] <= now.hour < hours[1]


def next_opening(now: datetime) -> datetime:
    """The next moment the store opens, strictly after `now` if it is open."""
    day = now.replace(minute=0, second=0, microsecond=0)
    for offset in range(8):
        candidate_day = day + timedelta(days=offset)
        hours = OPENING_HOURS.get(candidate_day.weekday())
        if hours is None:
            continue
        opening = candidate_day.replace(hour=hours[0])
        if opening > now:
            return opening
    raise AssertionError("the store opens at least once a week")
