"""Sức khỏe tài chính: the monthly savings rate against VWA's rule of thumb that it should be at least one's age in percent.

A rule of thumb from the VWA talk, not a standard; it reports and never advises."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

TARGET_CAP = Decimal("0.90")


def _vnd(value: Decimal) -> str:
    return format(value.quantize(Decimal(1), ROUND_HALF_UP), "f")


def wealth_check(*, income: Decimal, expenses: Decimal, birth_year: int, today: date) -> dict:
    age = today.year - birth_year  # by calendar year, so it changes on 1 January without asking for a birth date
    target = min(Decimal(age) / 100, TARGET_CAP)
    savings = income - expenses
    rate = savings / income if income > 0 else Decimal(0)
    need = target * income
    if savings <= 0:
        status = "none"
    elif savings >= need:
        status = "ok"
    else:
        status = "short"
    return {"age": age, "savings": _vnd(savings), "rate": str(rate.quantize(Decimal("0.0001"), ROUND_HALF_UP)),
            "target": str(target.quantize(Decimal("0.01"))), "status": status,
            "gap": _vnd(need - savings) if status != "ok" else None, "surplus": _vnd(savings - need) if status == "ok" else None}
