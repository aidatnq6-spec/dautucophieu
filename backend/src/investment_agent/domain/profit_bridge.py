"""Vì sao lợi nhuận quý thay đổi: parent net profit of the same quarter last year to this quarter's, line by line from the published
income statement (VNDirect, as stored by market/statements.py):

- revenue: the change in net revenue at last year's gross margin;
- margin: this quarter's revenue × the change in gross margin (the two add up to the change in gross profit exactly);
- selling, admin: the change in each cost, as it hits profit;
- financial: the change in financial income less financial expense;
- associates, other_profit: the change in each;
- tax, minority: the change in income tax and in the minority's share, as it hits parent profit;
- other: what no line explains (a line the layout reports elsewhere): shown on its own, never spread over the rest.

A line missing in either quarter counts as zero only for the optional lines (associates, other profit, minority); revenue and gross
profit are needed, so banks, brokers and insurers (another layout) get no bridge.
"""

from decimal import ROUND_HALF_UP, Decimal

NEEDED = ("revenue", "gross_profit")
OPTIONAL = ("selling", "admin", "fin_income", "fin_expense", "associates", "other_profit", "tax", "minority_profit")


def _s(v: Decimal) -> str:
    q = v.quantize(Decimal(1), ROUND_HALF_UP)
    return format(q, "f") if q != 0 else "0"


def _base(quarter: str) -> str:
    return f"{int(quarter[:4]) - 1}{quarter[4:]}"


def profit_bridge(quarters: dict[str, dict], quarter: str) -> dict:
    now, base = quarters.get(quarter) or {}, quarters.get(_base(quarter))
    if base is None:
        return {"status": "no_base", "quarter": quarter}
    missing = [k for k in (*NEEDED, "npat_parent") if now.get(k) is None or base.get(k) is None]
    if missing:
        return {"status": "missing_lines", "quarter": quarter, "missing": missing}
    n = {k: Decimal(now[k]) if now.get(k) is not None else Decimal(0) for k in (*NEEDED, *OPTIONAL, "npat_parent")}
    b = {k: Decimal(base[k]) if base.get(k) is not None else Decimal(0) for k in (*NEEDED, *OPTIONAL, "npat_parent")}
    if b["revenue"] == 0 or n["revenue"] == 0:
        return {"status": "missing_lines", "quarter": quarter, "missing": ["revenue"]}
    margin_b, margin_n = b["gross_profit"] / b["revenue"], n["gross_profit"] / n["revenue"]
    revenue = ((n["revenue"] - b["revenue"]) * margin_b).quantize(Decimal(1), ROUND_HALF_UP)
    steps = {"revenue": revenue, "margin": n["gross_profit"] - b["gross_profit"] - revenue,
             "selling": b["selling"] - n["selling"], "admin": b["admin"] - n["admin"],
             "financial": (n["fin_income"] - n["fin_expense"]) - (b["fin_income"] - b["fin_expense"]),
             "associates": n["associates"] - b["associates"], "other_profit": n["other_profit"] - b["other_profit"],
             "tax": b["tax"] - n["tax"], "minority": b["minority_profit"] - n["minority_profit"]}
    other = n["npat_parent"] - b["npat_parent"] - sum(steps.values(), Decimal(0))
    return {"status": "ok", "quarter": quarter, "base_quarter": _base(quarter), "start": _s(b["npat_parent"]), "end": _s(n["npat_parent"]),
            "margins": {"base": _s(margin_b * 10000), "now": _s(margin_n * 10000)},  # basis points
            "steps": [{"id": k, "amount": _s(v)} for k, v in steps.items()], "other": _s(other)}
