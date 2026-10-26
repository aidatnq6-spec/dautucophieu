"""Money for stocks: the owner's total financial assets, less protected needs, times the equity ratio of their risk group.

Held stocks are measured at cost (what was put in). Holding more than the budget is reported as an excess, never as a sell.
"""

from decimal import ROUND_HALF_UP, Decimal


def _s(value: Decimal) -> str:
    return format(value.quantize(Decimal(1), ROUND_HALF_UP), "f")


def equity_budget(*, total: Decimal | None, deductions: Decimal, group: str | None, ratios: dict[str, Decimal], held_cost: Decimal) -> dict:
    if total is None:
        return {"status": "no_total"}
    if group is None or group not in ratios:
        return {"status": "no_risk"}
    base = max(total - deductions, Decimal(0))
    ratio = ratios[group]
    budget = (base * ratio).quantize(Decimal(1), ROUND_HALF_UP)
    return {"status": "ok", "total": _s(total), "deductions": _s(deductions), "base": _s(base), "group": group, "ratio": str(ratio),
            "budget": _s(budget), "held_cost": _s(held_cost),
            "held_weight": str((held_cost / budget).quantize(Decimal("0.0001"), ROUND_HALF_UP)) if budget > 0 else None,
            "room": _s(budget - held_cost) if held_cost <= budget else None,
            "over": _s(held_cost - budget) if held_cost > budget else None}
