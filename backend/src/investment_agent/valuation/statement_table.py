"""Bảng số tài chính: quarterly and yearly tables of a non-financial company from VNDirect's statements, with the derived lines
and their checks. Nothing is estimated: a line whose parts are missing has no value.

Derived lines (đồng; costs shown negative):
- LN HĐKD lõi = gross profit − selling − administrative expenses. EBIT = profit before tax + interest expense. EBITDA = EBIT +
  depreciation. Margins over net revenue; growth against the same quarter a year before, or the year before.
- FCFF = operating cash flow + interest expense × (1 − effective tax rate) + capital spending (negative), the tax rate being the
  period's tax ÷ profit before tax; no value when profit before tax is not positive or the rate falls outside 0–100 %.
- Years: market capitalisation = the year's last adjusted close × today's share count (as the app's other P/E and P/B, so splits
  and bonus shares do not distort it); net debt = short + long borrowings − cash − short-term financial investments; EV =
  capitalisation + net debt + non-controlling interests; P/E on parent profit, P/B on parent equity (equity − non-controlling
  interests), EV/EBITDA, EV/revenue, FCFF yield = FCFF ÷ EV, ROE = parent profit ÷ average parent equity of the year and the one
  before.
- Summary: the last four quarters and today's close.
Checks (more than 0.5 % apart): gross profit against revenue − cost of sales; four quarters against the year for revenue, parent
profit, depreciation, capital spending and operating cash flow; parent profit against the free Vnstock statements.
"""

from decimal import ROUND_HALF_UP, Decimal

_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")
TOLERANCE = Decimal("0.005")
NEGATIVE = {"deductions", "cogs", "selling", "admin", "fin_expense", "interest", "tax"}
P_AND_L = [
    ("g", "Doanh thu"), ("gross_revenue", "Doanh thu bán hàng", "money", 0), ("deductions", "Các khoản giảm trừ", "money", 1),
    ("revenue", "Doanh thu thuần", "money", 0), ("revenue_yoy", "% so cùng kỳ", "pct", 1), ("cogs", "Giá vốn hàng bán", "money", 0),
    ("gross_profit", "Lợi nhuận gộp", "money", 0), ("gross_profit_yoy", "% so cùng kỳ", "pct", 1), ("gross_margin", "Biên gộp", "pct", 1),
    ("g", "Chi phí hoạt động"), ("selling", "Chi phí bán hàng", "money", 1), ("admin", "Chi phí quản lý doanh nghiệp", "money", 1),
    ("core_profit", "LN HĐKD lõi", "money", 0),
    ("g", "Tài chính và khác"), ("fin_income", "Doanh thu tài chính", "money", 1), ("fin_expense", "Chi phí tài chính", "money", 1),
    ("interest", "trong đó: lãi vay", "money", 1), ("associates", "LN liên doanh, liên kết", "money", 1), ("other_profit", "LN khác", "money", 1),
    ("pbt", "Lợi nhuận trước thuế", "money", 0), ("npat_parent", "LNST công ty mẹ", "money", 0), ("npat_parent_yoy", "% so cùng kỳ", "pct", 1),
    ("net_margin", "Biên ròng", "pct", 1),
    ("g", "EBIT · EBITDA"), ("ebit", "EBIT", "money", 0), ("ebit_margin", "Biên EBIT", "pct", 1), ("depreciation", "Khấu hao", "money", 1),
    ("ebitda", "EBITDA", "money", 0), ("ebitda_yoy", "% so cùng kỳ", "pct", 1), ("ebitda_margin", "Biên EBITDA", "pct", 1),
    ("g", "Dòng tiền"), ("cfo", "Lưu chuyển tiền từ HĐKD", "money", 0), ("capex", "Mua sắm TSCĐ (capex)", "money", 1),
    ("fcff", "FCFF", "money", 0),
]
SCALE = [
    ("g", "Quy mô và định giá"), ("market_cap", "Vốn hoá", "money", 0), ("debt", "Nợ vay", "money", 1),
    ("cash_like", "Tiền và đầu tư tài chính ngắn hạn", "money", 1), ("net_debt", "Nợ ròng", "money", 0), ("ev", "EV", "money", 0),
    ("pe", "P/E", "x", 0), ("pb", "P/B", "x", 0), ("ev_ebitda", "EV/EBITDA", "x", 0), ("ev_revenue", "EV/Doanh thu", "x", 0),
    ("fcff_yield", "Lợi suất FCFF", "pct", 0), ("roe", "ROE", "pct", 0),
]
SUMMED = (("revenue", "Doanh thu thuần"), ("npat_parent", "LNST công ty mẹ"), ("depreciation", "Khấu hao"), ("capex", "Capex"),
          ("cfo", "Lưu chuyển tiền từ HĐKD"))


def _d(v) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def _money(v: Decimal | None) -> str | None:
    return None if v is None else format(v.quantize(Decimal(1), ROUND_HALF_UP).normalize(), "f") if v != 0 else "0"


def _ratio(a: Decimal | None, b: Decimal | None, q: Decimal = _Q4, positive: bool = False) -> str | None:
    if a is None or b is None or b == 0 or (positive and (b <= 0 or a <= 0)):
        return None
    return str((a / b).quantize(q, ROUND_HALF_UP))


def _sum(*parts) -> Decimal | None:
    return None if any(p is None for p in parts) else sum(parts, Decimal(0))


def _minority(f: dict) -> Decimal:
    return _d(f.get("minority_equity")) or _d(f.get("minority_equity_outside")) or Decimal(0)  # an absent line is none reported


def _parent_equity(f: dict) -> Decimal | None:
    equity = _d(f.get("equity"))
    if equity is None:
        return None
    return equity - (_d(f.get("minority_equity")) or Decimal(0))  # before 2015 non-controlling interests sat outside equity


def _derived(f: dict) -> dict[str, Decimal | None]:
    g = {k: _d(v) for k, v in f.items()}
    out = dict(g)
    gp, sell, adm = g.get("gross_profit"), g.get("selling"), g.get("admin")
    out["core_profit"] = None if None in (gp, sell, adm) else gp - sell - adm
    out["ebit"] = _sum(g.get("pbt"), g.get("interest"))
    out["ebitda"] = _sum(out["ebit"], g.get("depreciation"))
    pbt, tax, cfo, capex, interest = g.get("pbt"), g.get("tax"), g.get("cfo"), g.get("capex"), g.get("interest")
    rate = tax / pbt if pbt is not None and tax is not None and pbt > 0 else None
    out["fcff"] = None if rate is None or not 0 <= rate <= 1 or None in (cfo, capex, interest) else cfo + interest * (1 - rate) + capex
    return out


def _prior(period: str) -> str:
    return f"{int(period[:4]) - 1}{period[4:]}"


def _part(periods: dict, keys: list[str], extra: dict[str, dict] | None = None, spec=P_AND_L) -> dict:
    d = {p: _derived(periods[p]) | (extra or {}).get(p, {}) for p in keys}
    def value(key, p):
        cur = d[p]
        if key.endswith("_yoy"):
            base = key[:-4]
            before = d.get(_prior(p)) or (_derived(periods[_prior(p)]) if _prior(p) in periods else None)
            a, b = cur.get(base), (before or {}).get(base)
            return None if a is None or b is None or b <= 0 else str(((a - b) / b).quantize(_Q4, ROUND_HALF_UP))
        if key == "gross_margin":
            return _ratio(cur.get("gross_profit"), cur.get("revenue"))
        if key in ("net_margin", "ebit_margin", "ebitda_margin"):
            return _ratio(cur.get({"net_margin": "npat_parent", "ebit_margin": "ebit", "ebitda_margin": "ebitda"}[key]), cur.get("revenue"))
        if key in ("pe", "pb", "ev_ebitda", "ev_revenue"):
            return cur.get(key)
        if key in ("fcff_yield", "roe"):
            return cur.get(key)
        v = cur.get(key)
        return _money(-v if key in NEGATIVE and v is not None else v)
    rows = []
    for item in spec:
        if item[0] == "g":
            rows.append({"key": None, "label": item[1], "kind": "group", "indent": 0, "values": []})
        else:
            key, label, kind, indent = item
            rows.append({"key": key, "label": label, "kind": kind, "indent": indent, "values": [value(key, p) for p in keys]})
    return {"periods": keys, "rows": rows}


def _year_end_close(closes, year: int) -> Decimal | None:
    inside = [c for t, c in closes if t.year == year]
    return Decimal(str(inside[-1])) * 1000 if inside else None


def _valuation(years: dict, closes, shares: int | None) -> dict[str, dict]:
    out = {}
    for y, f in years.items():
        d = _derived(f)
        close = _year_end_close(closes, int(y))
        cap = close * shares if close is not None and shares else None
        debt = _sum(d.get("st_debt"), d.get("lt_debt"))
        cash_like = _sum(d.get("cash"), d.get("st_investments"))
        net = None if debt is None or cash_like is None else debt - cash_like
        ev = None if cap is None or net is None else cap + net + _minority(f)
        parent, before = _parent_equity(f), _parent_equity(years.get(str(int(y) - 1), {}))
        out[y] = {"market_cap": cap, "debt": debt, "cash_like": cash_like, "net_debt": net, "ev": ev,
                  "pe": _ratio(cap, d.get("npat_parent"), _Q2, positive=True), "pb": _ratio(cap, parent, _Q2, positive=True),
                  "ev_ebitda": _ratio(ev, d.get("ebitda"), _Q2, positive=True), "ev_revenue": _ratio(ev, d.get("revenue"), _Q2, positive=True),
                  "fcff_yield": _ratio(d.get("fcff"), ev) if ev and ev > 0 else None,
                  "roe": _ratio(d.get("npat_parent"), (parent + before) / 2) if parent is not None and before is not None and parent + before > 0 else None}
    return out


def _summary(quarters: dict, closes, shares: int | None) -> dict | None:
    have = [p for p in sorted(quarters) if _d(quarters[p].get("npat_parent")) is not None]
    if not have:
        return None
    last = have[-1]
    window = [last]
    while len(window) < 4:
        window.append(_previous_quarter(window[-1]))
    figures = [_derived(quarters[p]) if p in quarters else {} for p in window]
    npat = _sum(*(f.get("npat_parent") for f in figures))
    ebitda = _sum(*(f.get("ebitda") for f in figures))
    latest = quarters[last]
    d = _derived(latest)
    cap = Decimal(str(closes[-1][1])) * 1000 * shares if closes and shares else None
    debt, cash_like = _sum(d.get("st_debt"), d.get("lt_debt")), _sum(d.get("cash"), d.get("st_investments"))
    ev = None if cap is None or debt is None or cash_like is None else cap + debt - cash_like + _minority(latest)
    parent, before = _parent_equity(latest), _parent_equity(quarters.get(_prior(last), {}))
    return {"period": last, "close_date": closes[-1][0].date().isoformat() if closes else None, "market_cap": _money(cap), "npat_ttm": _money(npat),
            "ebitda_ttm": _money(ebitda), "ev": _money(ev), "pe": _ratio(cap, npat, _Q2, positive=True), "pb": _ratio(cap, parent, _Q2, positive=True),
            "ev_ebitda": _ratio(ev, ebitda, _Q2, positive=True),
            "roe": _ratio(npat, (parent + before) / 2) if npat is not None and parent is not None and before is not None and parent + before > 0 else None,
            "quarters": list(reversed(window))}


def _previous_quarter(period: str) -> str:
    y, q = int(period[:4]), int(period[-1])
    return f"{y}-Q{q - 1}" if q > 1 else f"{y - 1}-Q4"


def _off(a: Decimal, b: Decimal, scale: Decimal) -> bool:
    return scale != 0 and abs(a - b) > TOLERANCE * abs(scale)


def _checks(quarters: dict, years: dict, vnstock: dict | None) -> list[dict]:
    out = []
    for periods in (quarters, years):
        for p, f in periods.items():
            rev, cogs, gp = _d(f.get("revenue")), _d(f.get("cogs")), _d(f.get("gross_profit"))
            if None not in (rev, cogs, gp) and _off(gp, rev - cogs, rev):
                out.append({"period": p, "check": "gross_profit", "label": "Lợi nhuận gộp ≠ doanh thu thuần − giá vốn", "a": _money(gp), "b": _money(rev - cogs)})
    for y, f in years.items():
        for key, label in SUMMED:
            parts = [_d(quarters.get(f"{y}-Q{k}", {}).get(key)) for k in (1, 2, 3, 4)]
            whole = _d(f.get(key))
            if whole is not None and None not in parts and _off(sum(parts), whole, whole):
                out.append({"period": y, "check": key, "label": f"{label}: tổng 4 quý ≠ cả năm", "a": _money(sum(parts)), "b": _money(whole)})
    for p, f in (vnstock or {}).items():
        a, b = _d(quarters.get(p, {}).get("npat_parent")), _d(f.get("npat"))
        if a is not None and b is not None and _off(a, b, b):
            out.append({"period": p, "check": "vnstock_npat", "label": "LNST công ty mẹ: VNDirect ≠ Vnstock", "a": _money(a), "b": _money(b)})
    return sorted(out, key=lambda c: (c["period"], c["check"]))


def statement_table(record: dict, *, closes, shares: int | None, vnstock: dict | None) -> dict:
    quarters, years = record.get("quarters", {}), record.get("years", {})
    valuation = _valuation(years, closes, shares)
    year_part = _part(years, sorted(years), extra=valuation, spec=P_AND_L + SCALE)
    for row in year_part["rows"]:  # money lines of the valuation block arrive as Decimals
        if row["kind"] == "money":
            row["values"] = [_money(v) if isinstance(v, Decimal) else v for v in row["values"]]
    return {"symbol": record.get("symbol"), "source": record.get("source"), "fetched_at": record.get("fetched_at"),
            "quarters": _part(quarters, sorted(quarters)), "years": year_part, "summary": _summary(quarters, closes, shares),
            "checks": _checks(quarters, years, vnstock),
            "conflicts": record.get("quarters_conflicts", []) + record.get("years_conflicts", [])}
