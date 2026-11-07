"""Dự phóng quý tới: the owner's assumptions for the quarter after the latest reported one, turned into the lines of Bảng số
tài chính (the yellow "F" column). A scenario the owner sets, not a forecast of the application: nothing is assumed for them, and
a line resting on a blank assumption stays blank.

Revenue = the same quarter a year before × (1 + growth). Cost of sales = revenue × (1 − gross margin); selling and administrative
expenses as shares of revenue; financial income and expense, interest (part of the financial expense), associates and other profit
in tỷ đồng; profit before tax = core profit + financial income − financial expense + associates + other profit; parent profit =
profit before tax × (1 − tax rate) × (1 − non-controlling share); EBIT = profit before tax + interest; EBITDA = EBIT + depreciation.
Costs are shown negative, as in the table. Growth of parent profit against the same quarter a year before.
"""

from decimal import ROUND_HALF_UP, Decimal

FIELDS = ("revenue_yoy", "gross_margin", "selling_pct", "admin_pct", "fin_income", "fin_expense", "interest", "associates", "other_profit",
          "tax_rate", "minority_pct", "depreciation")
RATES = {"revenue_yoy", "gross_margin", "selling_pct", "admin_pct", "tax_rate", "minority_pct"}  # decimals; the rest in tỷ đồng
_Q4 = Decimal("0.0001")
_TY = Decimal(10**9)


def _money(v: Decimal | None) -> str | None:
    return None if v is None else format(v.quantize(Decimal(1), ROUND_HALF_UP).normalize(), "f") if v != 0 else "0"


def _ratio(a: Decimal | None, b: Decimal | None) -> str | None:
    return None if a is None or b is None or b == 0 else str((a / b).quantize(_Q4, ROUND_HALF_UP))


def _quarter(period: str) -> tuple[int, int]:
    return int(period[:4]), int(period[-1])


def next_quarter(quarters: dict) -> str | None:
    if not quarters:
        return None
    y, q = _quarter(max(quarters))
    return f"{y}-Q{q + 1}" if q < 4 else f"{y + 1}-Q1"


def _all(*parts):
    return None if any(p is None for p in parts) else parts


def forecast_quarter(quarters: dict, quarter: str, assumptions: dict) -> dict:
    y, q = _quarter(quarter)
    base_key = f"{y - 1}-Q{q}"
    base = quarters.get(base_key) or {}
    if base.get("revenue") is None:
        return {"quarter": quarter, "base": base_key, "values": {}, "reason": f"Chưa có doanh thu Q{q}/{y - 1} để làm gốc so cùng kỳ"}
    a = {k: (Decimal(str(assumptions[k])) if assumptions.get(k) not in (None, "") else None) for k in FIELDS}
    for k in FIELDS:
        if a[k] is not None and k not in RATES:
            a[k] *= _TY
    revenue = Decimal(base["revenue"]) * (1 + a["revenue_yoy"]) if a["revenue_yoy"] is not None else None
    gross = revenue * a["gross_margin"] if _all(revenue, a["gross_margin"]) else None
    cogs = revenue - gross if gross is not None else None
    selling = revenue * a["selling_pct"] if _all(revenue, a["selling_pct"]) else None
    admin = revenue * a["admin_pct"] if _all(revenue, a["admin_pct"]) else None
    core = gross - selling - admin if _all(gross, selling, admin) else None
    pbt = core + a["fin_income"] - a["fin_expense"] + a["associates"] + a["other_profit"] \
        if _all(core, a["fin_income"], a["fin_expense"], a["associates"], a["other_profit"]) else None
    parent = pbt * (1 - a["tax_rate"]) * (1 - a["minority_pct"]) if _all(pbt, a["tax_rate"], a["minority_pct"]) else None
    ebit = pbt + a["interest"] if _all(pbt, a["interest"]) else None
    ebitda = ebit + a["depreciation"] if _all(ebit, a["depreciation"]) else None
    neg = lambda v: -v if v is not None else None  # noqa: E731
    before = Decimal(base["npat_parent"]) if base.get("npat_parent") is not None else None
    values = {"revenue": _money(revenue), "revenue_yoy": _ratio(revenue - Decimal(base["revenue"]), Decimal(base["revenue"])) if revenue is not None else None,
              "cogs": _money(neg(cogs)), "gross_profit": _money(gross), "gross_margin": _ratio(gross, revenue), "selling": _money(neg(selling)),
              "admin": _money(neg(admin)), "core_profit": _money(core), "fin_income": _money(a["fin_income"]), "fin_expense": _money(neg(a["fin_expense"])),
              "interest": _money(neg(a["interest"])), "associates": _money(a["associates"]), "other_profit": _money(a["other_profit"]),
              "pbt": _money(pbt), "npat_parent": _money(parent),
              "npat_parent_yoy": _ratio(parent - before, before) if parent is not None and before is not None and before > 0 else None,
              "net_margin": _ratio(parent, revenue), "ebit": _money(ebit), "ebit_margin": _ratio(ebit, revenue), "depreciation": _money(a["depreciation"]),
              "ebitda": _money(ebitda), "ebitda_margin": _ratio(ebitda, revenue)}
    return {"quarter": quarter, "base": base_key, "values": values, "reason": None}
