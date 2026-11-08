"""Bảng số tài chính: quarterly and yearly tables of a non-financial company from VNDirect's statements, with the derived lines
and their checks. Nothing is estimated: a line whose parts are missing has no value.

Derived lines (đồng; costs shown negative):
- LN HĐKD lõi = gross profit − selling − administrative expenses. EBIT = profit before tax + interest expense. EBITDA = EBIT +
  depreciation. Margins over net revenue; growth against the same quarter a year before, or the year before.
- FCFF = operating cash flow + interest expense × (1 − effective tax rate) + capital spending (negative), the tax rate being the
  period's tax ÷ profit before tax; no value when profit before tax is not positive or the rate falls outside 0–100 %.
- Years: market capitalisation = the year's last unadjusted close (VNDirect, from 2013) × that year-end's shares (charter capital ÷
  10,000 đ par), as the market valued it then; no value without both; net debt = short + long borrowings − cash − short-term financial investments; EV =
  capitalisation + net debt + non-controlling interests; P/E on parent profit, P/B on parent equity (equity − non-controlling
  interests), EV/EBITDA, EV/revenue, FCFF yield = FCFF ÷ EV, ROE = parent profit ÷ average parent equity of the year and the one
  before.
- Quarters: the same block at the quarter's last unadjusted close × that quarter-end's shares and balance sheet; P/E, EV/EBITDA,
  EV/revenue, FCFF yield and ROE on the four quarters to it (ROE over the average parent equity of the quarter and the same quarter a
  year before); none when one of the four quarters is missing.
- Banks and securities firms (kind): only a scale and valuation block, by quarter (four quarters to it) and by year: market cap,
  parent equity, book value per share, P/B, P/E, ROE; banks add capitalisation ÷ profit before provisions and ÷ total operating
  income, securities firms borrowings ÷ equity and capitalisation ÷ operating revenue, insurers capitalisation ÷ net premium,
  investments (cash, short and long-term financial investments) ÷ equity, and the insurance and investment results (four quarters
  in the quarterly view); the insurance result only where the parts add up to profit before tax, listed as a check where they do
  not. No net debt, EV, EBITDA or FCFF.
- Summary: the last four quarters and today's close.
Checks (more than 0.5 % apart): gross profit against revenue − cost of sales; four quarters against the year for revenue, parent
profit, depreciation, capital spending and operating cash flow; parent profit against the free Vnstock statements.
"""

from decimal import ROUND_HALF_UP, Decimal

_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")
TOLERANCE = Decimal("0.005")
PAR = Decimal(10000)  # đồng per share: charter capital ÷ par = shares at the period's end
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
    ("fcff_yield", "Lợi suất FCFF", "pct", 0), ("roe", "ROE", "pct", 0), ("debt_to_equity", "Vay / vốn chủ", "x", 0),
]
_FIN_HEAD = [("g", "Quy mô và định giá"), ("market_cap", "Vốn hoá", "money", 0), ("parent_equity", "Vốn chủ công ty mẹ", "money", 0),
             ("bvps", "Giá trị sổ sách / cổ phiếu", "vnd", 0), ("pb", "P/B", "x", 0), ("pe", "P/E", "x", 0), ("roe", "ROE", "pct", 0)]
# Banks and securities firms: borrowing is their trade, so net debt, EV, EBITDA and FCFF say nothing; their block stands alone.
FIN_SCALE = {"bank": _FIN_HEAD + [("p_ppop", "Vốn hoá / LN trước dự phòng", "x", 0), ("p_toi", "Vốn hoá / Tổng thu nhập hoạt động", "x", 0)],
             "securities": _FIN_HEAD + [("debt_to_equity", "Vay / vốn chủ", "x", 0), ("p_revenue", "Vốn hoá / Doanh thu hoạt động", "x", 0)],
             "insurance": _FIN_HEAD + [("p_premium", "Vốn hoá / Doanh thu phí bảo hiểm thuần", "x", 0),
                                       ("investments_to_equity", "Danh mục đầu tư / vốn chủ", "x", 0),
                                       ("ins_result", "Kết quả kinh doanh bảo hiểm", "money", 0), ("fin_profit", "Lợi nhuận hoạt động tài chính", "money", 0)]}
FIN_FLOW_ROWS = {"ins_result", "fin_profit"}  # money over the period: four quarters in the quarterly view
INS_PARTS = ("ins_result", "fin_profit", "other_ops", "other_profit", "associates_before", "associates")
SUMMED = (("revenue", "Doanh thu thuần"), ("npat_parent", "LNST công ty mẹ"), ("depreciation", "Khấu hao"), ("capex", "Capex"),
          ("cfo", "Lưu chuyển tiền từ HĐKD"), ("ppop", "LN trước dự phòng"), ("operating_income", "Tổng thu nhập hoạt động"),
          ("operating_revenue", "Doanh thu hoạt động"), ("net_premium", "Doanh thu phí bảo hiểm thuần"),
          ("fin_profit", "Lợi nhuận hoạt động tài chính"))


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
        if key in ("pe", "pb", "ev_ebitda", "ev_revenue", "debt_to_equity"):
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


def _block(f: dict, close: Decimal | None, flows: dict[str, Decimal | None], parent_before: Decimal | None) -> dict:
    """Scale and valuation at a period's end: its close × its shares, its balance sheet, and the profit and cash of `flows`."""
    d = _derived(f)
    capital = _d(f.get("charter_capital"))
    cap = close * 1000 * (capital / PAR) if close is not None and capital is not None and capital > 0 else None
    debt = _sum(d.get("st_debt"), d.get("lt_debt"))
    cash_like = _sum(d.get("cash"), d.get("st_investments"))
    net = None if debt is None or cash_like is None else debt - cash_like
    ev = None if cap is None or net is None else cap + net + _minority(f)
    parent, npat, equity = _parent_equity(f), flows.get("npat_parent"), _d(f.get("equity"))
    return {"market_cap": cap, "debt": debt, "cash_like": cash_like, "net_debt": net, "ev": ev,
            "debt_to_equity": _ratio(debt, equity, _Q2) if equity is not None and equity > 0 and debt is not None else None,
            "pe": _ratio(cap, npat, _Q2, positive=True), "pb": _ratio(cap, parent, _Q2, positive=True),
            "ev_ebitda": _ratio(ev, flows.get("ebitda"), _Q2, positive=True), "ev_revenue": _ratio(ev, flows.get("revenue"), _Q2, positive=True),
            "fcff_yield": _ratio(flows.get("fcff"), ev) if ev and ev > 0 and flows.get("fcff") is not None else None,
            "roe": _ratio(npat, (parent + parent_before) / 2)
            if npat is not None and parent is not None and parent_before is not None and parent + parent_before > 0 else None}


FLOWS = ("npat_parent", "ebitda", "revenue", "fcff")


def _valuation(years: dict, year_end_close: dict) -> dict[str, dict]:
    out = {}
    for y, f in years.items():
        d = _derived(f)
        out[y] = _block(f, _d((year_end_close.get(y) or {}).get("close")), {k: d.get(k) for k in FLOWS},
                        _parent_equity(years.get(str(int(y) - 1), {})))
    return out


def _quarter_valuation(quarters: dict, quarter_end_close: dict) -> dict[str, dict]:
    """Each quarter at its last session's close, its multiples and ROE on the four quarters to it (none when one is missing)."""
    out = {}
    for p, f in quarters.items():
        out[p] = _block(f, _d((quarter_end_close.get(p) or {}).get("close")), _four(quarters, p, FLOWS), _parent_equity(quarters.get(_prior(p), {})))
    return out


FIN_FLOWS = ("npat_parent", "ppop", "operating_income", "operating_revenue", "net_premium", "ins_result", "fin_profit")


def _reconciles(f: dict) -> bool:
    """An insurer's parts add up to its profit before tax (true of the layout from mid-2014, not of the one before)."""
    pbt, parts = _d(f.get("pbt")), [_d(f.get(k)) or Decimal(0) for k in INS_PARTS]
    return pbt is not None and f.get("ins_result") is not None and not _off(sum(parts, Decimal(0)), pbt, max(abs(pbt), Decimal(10**9)))


def _insurer(periods: dict) -> dict:
    """The periods with the insurance result kept only where the parts add up."""
    return {p: (f if _reconciles(f) else {k: v for k, v in f.items() if k != "ins_result"}) for p, f in periods.items()}


def _fin_block(f: dict, close: Decimal | None, flows: dict[str, Decimal | None], parent_before: Decimal | None) -> dict:
    """A bank's or securities firm's block at a period's end: its close × its shares and equity, with the profit of `flows`."""
    capital = _d(f.get("charter_capital"))
    shares = capital / PAR if capital is not None and capital > 0 else None
    cap = close * 1000 * shares if close is not None and shares is not None else None
    parent, equity, npat = _parent_equity(f), _d(f.get("equity")), flows.get("npat_parent")
    debt = _sum(_d(f.get("st_debt")), _d(f.get("lt_debt")))
    return {"market_cap": cap, "parent_equity": parent,
            "bvps": None if parent is None or shares is None else _money(parent / shares),
            "pb": _ratio(cap, parent, _Q2, positive=True), "pe": _ratio(cap, npat, _Q2, positive=True),
            "roe": _ratio(npat, (parent + parent_before) / 2)
            if npat is not None and parent is not None and parent_before is not None and parent + parent_before > 0 else None,
            "p_ppop": _ratio(cap, flows.get("ppop"), _Q2, positive=True), "p_toi": _ratio(cap, flows.get("operating_income"), _Q2, positive=True),
            "debt_to_equity": _ratio(debt, equity, _Q2) if equity is not None and equity > 0 else None,
            "p_revenue": _ratio(cap, flows.get("operating_revenue"), _Q2, positive=True),
            "p_premium": _ratio(cap, flows.get("net_premium"), _Q2, positive=True),
            "investments_to_equity": _ratio(_sum(_d(f.get("cash")), _d(f.get("st_investments")), _d(f.get("lt_investments"))), equity, _Q2)
            if equity is not None and equity > 0 else None,
            "ins_result": flows.get("ins_result"), "fin_profit": flows.get("fin_profit")}


def _four(quarters: dict, p: str, keys) -> dict[str, Decimal | None]:
    """Each of `keys` added over the four quarters to p; none when one of them is missing."""
    window = [p]
    while len(window) < 4:
        window.append(_previous_quarter(window[-1]))
    figures = [_derived(quarters[w]) if w in quarters else {} for w in window]
    return {k: _sum(*(x.get(k) for x in figures)) for k in keys}


def _fin_part(periods: dict, blocks: dict[str, dict], spec, four: bool = False) -> dict:
    keys = sorted(periods)
    rows = []
    for item in spec:
        if item[0] == "g":
            rows.append({"key": None, "label": item[1], "kind": "group", "indent": 0, "values": []})
            continue
        key, label, kind, indent = item
        values = [blocks[p].get(key) for p in keys]
        rows.append({"key": key, "label": f"{label} (4 quý)" if four and key in FIN_FLOW_ROWS else label, "kind": kind, "indent": indent,
                     "values": [_money(v) if isinstance(v, Decimal) else v for v in values]})
    return {"periods": keys, "rows": rows}


def _fin_table(record: dict, kind: str, vnstock: dict | None) -> dict:
    raw_q, raw_y = record.get("quarters", {}), record.get("years", {})
    quarters, years = (_insurer(raw_q), _insurer(raw_y)) if kind == "insurance" else (raw_q, raw_y)
    qclose, yclose = record.get("quarter_end_close", {}), record.get("year_end_close", {})
    q = {p: _fin_block(f, _d((qclose.get(p) or {}).get("close")), _four(quarters, p, FIN_FLOWS), _parent_equity(quarters.get(_prior(p), {})))
         for p, f in quarters.items()}
    y = {p: _fin_block(f, _d((yclose.get(p) or {}).get("close")), {k: _d(f.get(k)) for k in FIN_FLOWS},
                       _parent_equity(years.get(str(int(p) - 1), {}))) for p, f in years.items()}
    return {"symbol": record.get("symbol"), "source": record.get("source"), "fetched_at": record.get("fetched_at"),
            "quarters": _fin_part(quarters, q, FIN_SCALE[kind], four=True), "years": _fin_part(years, y, FIN_SCALE[kind]), "summary": None,
            "checks": sorted(_checks(quarters, years, vnstock) + (_ins_checks(raw_q) + _ins_checks(raw_y) if kind == "insurance" else []),
                             key=lambda c: (c["period"], c["check"])),
            "conflicts": record.get("quarters_conflicts", []) + record.get("years_conflicts", [])}


def _ins_checks(periods: dict) -> list[dict]:
    out = []
    for p, f in periods.items():
        pbt = _d(f.get("pbt"))
        if f.get("ins_result") is not None and pbt is not None and not _reconciles(f):
            out.append({"period": p, "check": "ins_reconcile", "label": "Kết quả kinh doanh bảo hiểm để trống: các phần không cộng ra LNTT (mẫu báo cáo cũ)",
                        "a": _money(sum((_d(f.get(k)) or Decimal(0) for k in INS_PARTS), Decimal(0))), "b": _money(pbt)})
    return out


def _market_value_now(record: dict, closes) -> tuple[Decimal | None, str | None]:
    """Today's market value and the quarter it starts from: that quarter's unadjusted close × its shares (charter capital ÷ par), moved
    by the adjusted series since that session, so a bonus issue or split after the quarter does not change it. Shares derived from
    profit and EPS are not used, they miss by up to double. None without that session in the series."""
    quarters, qclose = record.get("quarters", {}), record.get("quarter_end_close", {})
    based = [p for p in sorted(quarters) if p in qclose and _d(quarters[p].get("charter_capital"))]
    if not closes or not based:
        return None, None
    last = based[-1]
    then = next((Decimal(str(v)) for t, v in closes if t.date().isoformat() == qclose[last].get("date")), None)
    close = _d(qclose[last].get("close"))
    if not then or close is None:
        return None, None
    return close * 1000 * _d(quarters[last]["charter_capital"]) / PAR * Decimal(str(closes[-1][1])) / then, last


def _summary(record: dict, closes) -> dict | None:
    quarters = record.get("quarters", {})
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
    cap = _market_value_now(record, closes)[0]
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


def _current(record: dict, closes) -> dict:
    """P/E and P/B at the latest close, on the quarter its market value starts from. Blank as _market_value_now is."""
    quarters = record.get("quarters", {})
    close_date = closes[-1][0].date().isoformat() if closes else None
    cap, last = _market_value_now(record, closes)
    if cap is None:
        return {"pe": None, "pb": None, "close_date": close_date}
    npat = _four(quarters, last, ("npat_parent",))["npat_parent"]
    return {"pe": _ratio(cap, npat, _Q2, positive=True), "pb": _ratio(cap, _parent_equity(quarters[last]), _Q2, positive=True), "close_date": close_date}


def statement_table(record: dict, *, closes, vnstock: dict | None, kind: str | None = None) -> dict:
    if kind in FIN_SCALE:
        return {**_fin_table(record, kind, vnstock), "current": _current(record, closes)}
    quarters, years = record.get("quarters", {}), record.get("years", {})
    year_part = _part(years, sorted(years), extra=_valuation(years, record.get("year_end_close", {})), spec=P_AND_L + SCALE)
    quarter_part = _part(quarters, sorted(quarters), extra=_quarter_valuation(quarters, record.get("quarter_end_close", {})), spec=P_AND_L + SCALE)
    for row in year_part["rows"] + quarter_part["rows"]:  # money lines of the valuation block arrive as Decimals
        if row["kind"] == "money":
            row["values"] = [_money(v) if isinstance(v, Decimal) else v for v in row["values"]]
    return {"symbol": record.get("symbol"), "source": record.get("source"), "fetched_at": record.get("fetched_at"),
            "quarters": quarter_part, "years": year_part, "summary": _summary(record, closes),
            "current": _current(record, closes),
            "checks": _checks(quarters, years, vnstock),
            "conflicts": record.get("quarters_conflicts", []) + record.get("years_conflicts", [])}
