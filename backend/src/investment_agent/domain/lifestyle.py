"""Lạm phát lối sống: monthly spending against monthly income (and CPI) over a year, or at least six months. It names the pattern the
VWA talk warns about — spending rising faster than income — and never advises."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

MIN_MONTHS = 6


def _index(key: str) -> int:
    y, m = map(int, key.split("-"))
    return y * 12 + m - 1


def _key(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _change(new: Decimal, old: Decimal) -> Decimal:
    return new / old - 1 if old else Decimal(0)


def lifestyle_inflation(history: dict[str, dict], *, cpi: str | None, today: date) -> dict:
    """history: {"YYYY-MM": {income, expenses}}. Compares the latest month with the same month a year earlier when stored, otherwise
    with the earliest month at least six months before it."""
    months = sorted(k for k in history if _index(k) <= today.year * 12 + today.month - 1)
    out = {"from": None, "to": None, "months": None, "spending_change": None, "income_change": None, "cpi": cpi, "verdict": None, "ready_on": None}
    if not months:
        return out
    latest = months[-1]
    year_ago = _key(_index(latest) - 12)
    base = year_ago if year_ago in history else next((k for k in months if _index(latest) - _index(k) >= MIN_MONTHS), None)
    if base is None:
        return {**out, "ready_on": _key(_index(months[0]) + MIN_MONTHS)}
    new, old = history[latest], history[base]
    spending = _change(Decimal(new["expenses"]), Decimal(old["expenses"]))
    income = _change(Decimal(new["income"]), Decimal(old["income"]))
    if spending > income:
        verdict = "faster_than_income"
    elif cpi is not None and spending > Decimal(cpi) / 100:
        verdict = "faster_than_inflation"
    else:
        verdict = "ok"
    q = lambda d: str(d.quantize(Decimal("0.0001"), ROUND_HALF_UP))  # noqa: E731
    return {**out, "from": base, "to": latest, "months": _index(latest) - _index(base), "spending_change": q(spending), "income_change": q(income),
            "verdict": verdict, "from_values": old, "to_values": new}
