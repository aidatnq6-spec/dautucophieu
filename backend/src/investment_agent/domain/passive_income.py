"""Mục tiêu dòng tiền thụ động: the capital that would pay a monthly income at an assumed yearly rate, the income today's capital would
pay, and roughly how long until the target with monthly contributions reinvested at that rate. In today's money: inflation is not
modelled. An estimate, not advice."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

HORIZON_MONTHS = 600  # 50 years


def _vnd(value: Decimal) -> str:
    return format(value.quantize(Decimal(1), ROUND_HALF_UP), "f")


def _month_after(today: date, months: int) -> str:
    y, m = divmod(today.month - 1 + months, 12)
    return f"{today.year + y:04d}-{m + 1:02d}"


def passive_income(*, target: Decimal, rate: Decimal, capital: Decimal | None, contribution: Decimal, today: date) -> dict:
    """target: đồng per month; rate: percent per year (> 0); capital: investable assets now (None when unknown)."""
    yearly = rate / 100
    required = target * 12 / yearly
    income_now = capital * yearly / 12 if capital is not None else None
    progress = min(income_now / target, Decimal(1)) if income_now is not None else None
    value, months, monthly = capital or Decimal(0), 0, yearly / 12
    while value < required and months < HORIZON_MONTHS:
        value = value * (1 + monthly) + contribution
        months += 1
    reached = value >= required
    return {"required": _vnd(required), "income_now": _vnd(income_now) if income_now is not None else None,
            "progress": str(progress.quantize(Decimal("0.0001"), ROUND_HALF_UP)) if progress is not None else None,
            "months": months if reached else None, "reached_on": _month_after(today, months) if reached else None}
