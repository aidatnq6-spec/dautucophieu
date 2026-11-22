"""Nợ vay ròng and Tiền khách trả trước: two readings of a non-financial company's balance sheet, from its public statements.

Net debt = short- and long-term borrowing − cash − short-term investments; below zero the company holds more cash than it owes
banks (net cash). Borrowing that at least doubled in two years is flagged when it is a material part of the balance sheet. A
sector adds up its tickers' borrowing each quarter. For a property developer, money customers paid ahead (người mua trả tiền
trước, short and long term) against the same quarter a year before: profit jumping while those advances fall reads as handing
over homes already paid for; advances rising reads as money collected for homes still to be handed over. A missing line leaves
its figure blank; nothing is filled in. Readings, not advice.

Thang thanh khoản: cash (tiền và tương đương tiền, deposits up to three months included) and short-term financial investments
(mostly deposits of three to twelve months, also trading securities) against short-term borrowing, and their share of total assets.
Chênh lệch lãi vay – lãi gửi: over the last four quarters, financial income on the average of cash and short-term investments
against interest on the average borrowing (five quarter ends). Financial income also holds exchange gains and dividends received, so
the yield is a rough reading; "carry" names a company that borrows and keeps cash, both at least 5% of total assets, earning more on
the one than it pays on the other (borrowing cheap to deposit dear).

Phải thu: receivables by part, short and long term added (customers, prepayments to suppliers, loans, other receivables, the
bad-debt provision) and their share of total assets; số ngày thu tiền = short-term customer receivables at the quarter's end ÷ the
last four quarters' revenue × 365, against a year before and the median of the sector's watched tickers; dự phòng phải thu khó đòi
(short term) as a share of gross short-term receivables, "jump" when it grew by half or more in a year and is at least 1% of them.

Trả trước cho người bán is paid back in goods or services, never in money: số ngày ứng trước = prepayments to suppliers at the quarter's
end ÷ the last four quarters' cost of sales × 365, against a year before and the sector. Trả trước tăng cùng đợt huy động vốn: in the
quarter a share issue that raised money (not bonus shares) entered the charter capital, and the quarter after, prepayments to suppliers
grew by at least half of the capital added, a way money just raised can leave the company (to related parties above all)."""

from decimal import ROUND_HALF_UP, Decimal

_Q4 = Decimal("0.0001")
FAST_BORROWING = Decimal(2)  # borrowing at least twice what it was eight quarters before
MATERIAL_DEBT = Decimal("0.05")  # ... and at least 5% of total assets, so a tiny loan doubling is not flagged
HANDOVER_ADVANCES = Decimal("-0.10")  # advances down 10% or more against a year before
HANDOVER_PROFIT = Decimal("0.50")  # while the quarter's parent profit is up 50% or more (or turned from a loss)
COLLECTING_ADVANCES = Decimal("0.20")  # advances up 20% or more against a year before
# Bounds of a plain reading of Chênh lệch lãi vay – lãi gửi: above 10% a year no deposit pays it (the financial income holds exchange
# gains, gains on investments or lending), below 2% a year no bank lends at it (interest capitalised into projects or assets being
# built, common among property developers); either way the figures are shown and named, and the company is not called carry.
DEPOSIT_YIELD_CEILING, LOAN_COST_FLOOR = Decimal("0.10"), Decimal("0.02")


def _d(v) -> Decimal | None:
    try:
        return Decimal(str(v)) if v is not None else None
    except ArithmeticError:
        return None


def _s(v: Decimal | None) -> str | None:
    return format(v, "f") if v is not None else None


def _r(v: Decimal | None) -> str | None:
    return str(v.quantize(_Q4, ROUND_HALF_UP)) if v is not None else None


def _back(period: str, quarters: int) -> str:
    y, n = (int(x) for x in period.split("-Q"))
    k = y * 4 + (n - 1) - quarters
    return f"{k // 4}-Q{k % 4 + 1}"


def _get(q: dict, *fields: str) -> list[Decimal | None]:
    return [_d((q or {}).get(f)) for f in fields]


def _debt(q: dict) -> Decimal | None:
    st, lt = _get(q, "st_debt", "lt_debt")
    return st + lt if st is not None and lt is not None else None


def _net_debt(q: dict) -> Decimal | None:
    debt, (cash, inv) = _debt(q), _get(q, "cash", "st_investments")
    return debt - cash - inv if None not in (debt, cash, inv) else None


def net_debt_rows(quarters: dict, n: int = 12) -> list[dict]:
    """The last n quarters, oldest first: borrowing, cash, net debt, whether that is net cash, and borrowing ÷ equity."""
    out = []
    for period in sorted(quarters)[-n:]:
        q = quarters[period]
        debt, net = _debt(q), _net_debt(q)
        cash, inv, equity = _get(q, "cash", "st_investments", "equity")
        out.append({"quarter": period, "debt": _s(debt), "cash": _s(cash + inv if cash is not None and inv is not None else None),
                    "net_debt": _s(net), "net_cash": (net < 0) if net is not None else None,
                    "debt_to_equity": _r(debt / equity) if debt is not None and equity and equity > 0 else None})
    return out


def borrowing_flag(quarters: dict) -> dict:
    """The latest quarter's borrowing against eight quarters before. kind "fast_borrowing" when it at least doubled (or started from
    nothing) and is at least 5% of total assets; None otherwise or when either end is missing."""
    latest = next((p for p in sorted(quarters, reverse=True) if _debt(quarters[p]) is not None), None)
    if latest is None:
        return {"kind": None, "quarter": None, "debt": None, "debt_2y_ago": None, "ratio": None}
    debt, ago = _debt(quarters[latest]), _debt(quarters.get(_back(latest, 8), {}))
    (assets,) = _get(quarters[latest], "total_assets")
    ratio = debt / ago if ago is not None and ago > 0 else None
    material = assets is not None and assets > 0 and debt >= MATERIAL_DEBT * assets
    fast = ago is not None and material and ((ratio is not None and ratio >= FAST_BORROWING) or (ago == 0 and debt > 0))
    return {"kind": "fast_borrowing" if fast else None, "quarter": latest, "debt": _s(debt), "debt_2y_ago": _s(ago), "ratio": _r(ratio)}


def sector_debt(records: dict[str, dict], n: int = 12) -> dict:
    """A sector's borrowing and net debt each quarter over the tickers that report it (count says how many), and the change over two
    years in the latest quarter on the tickers that have both ends, with the ticker adding most to it."""
    periods = sorted({p for quarters in records.values() for p in quarters})[-n:]
    rows = []
    for p in periods:
        debts = [d for d in (_debt(r.get(p, {})) for r in records.values()) if d is not None]
        nets = [d for d in (_net_debt(r.get(p, {})) for r in records.values()) if d is not None]
        rows.append({"quarter": p, "count": len(debts), "debt": _s(sum(debts)) if debts else None, "net_debt": _s(sum(nets)) if nets else None,
                     "net_count": len(nets)})
    growth, compared, top = None, 0, None
    if periods:
        last, ago = periods[-1], _back(periods[-1], 8)
        pairs = {s: (_debt(r.get(last, {})), _debt(r.get(ago, {}))) for s, r in records.items()}
        pairs = {s: v for s, v in pairs.items() if None not in v}
        now, before = sum((v[0] for v in pairs.values()), Decimal(0)), sum((v[1] for v in pairs.values()), Decimal(0))
        compared = len(pairs)
        growth = now / before - 1 if pairs and before > 0 else None
        top = max(pairs, key=lambda s: pairs[s][0] - pairs[s][1], default=None)
    return {"quarters": rows, "growth_2y": _r(growth), "compared": compared, "top": top}


def _cash_like(q: dict) -> Decimal | None:
    cash, inv = _get(q, "cash", "st_investments")
    return cash + inv if cash is not None and inv is not None else None


def liquidity_rows(quarters: dict, n: int = 12) -> list[dict]:
    """The last n quarters, oldest first: cash, short-term investments, both together, short-term borrowing, how many times the
    first covers the second (None without short-term borrowing), and the cash's share of total assets."""
    out = []
    for period in sorted(quarters)[-n:]:
        q = quarters[period]
        cash, inv, st_debt, assets = _get(q, "cash", "st_investments", "st_debt", "total_assets")
        like = _cash_like(q)
        out.append({"quarter": period, "cash": _s(cash), "st_investments": _s(inv), "cash_like": _s(like), "st_debt": _s(st_debt),
                    "cover": _r(like / st_debt) if like is not None and st_debt else None,
                    "cash_share": _r(like / assets) if like is not None and assets and assets > 0 else None})
    return out


def carry(quarters: dict) -> dict:
    """The last four quarters to the latest one with financial income: their financial income and interest, the average cash and
    short-term investments and the average borrowing over the five quarter ends, the yield on the one, the cost of the other and the
    spread. A quarter missing any of these is named in missing, and nothing is computed."""
    latest = next((p for p in sorted(quarters, reverse=True) if _get(quarters[p], "fin_income")[0] is not None), None)
    empty = {"quarter": latest, "kind": None, "missing": [], "fin_income": None, "interest": None, "net": None, "avg_cash_like": None,
             "avg_debt": None, "yield": None, "cost": None, "spread": None}
    if latest is None:
        return empty
    flows = [_back(latest, k) for k in range(3, -1, -1)]
    ends = [_back(latest, 4), *flows]
    missing = sorted({p for p in flows if None in _get(quarters.get(p, {}), "fin_income", "interest")}
                     | {p for p in ends if _cash_like(quarters.get(p, {})) is None or _debt(quarters.get(p, {})) is None})
    if missing:
        return {**empty, "missing": missing}
    income = sum((_get(quarters[p], "fin_income")[0] for p in flows), Decimal(0))
    interest = sum((_get(quarters[p], "interest")[0] for p in flows), Decimal(0))
    avg_cash = sum((_cash_like(quarters[p]) for p in ends), Decimal(0)) / len(ends)
    avg_debt = sum((_debt(quarters[p]) for p in ends), Decimal(0)) / len(ends)
    earned = income / avg_cash if avg_cash > 0 else None
    cost = interest / avg_debt if avg_debt > 0 else None
    spread = earned - cost if earned is not None and cost is not None else None
    (assets,) = _get(quarters[latest], "total_assets")
    material = assets is not None and assets > 0 and avg_debt >= MATERIAL_DEBT * assets and avg_cash >= MATERIAL_DEBT * assets
    if avg_debt == 0:
        kind = "no_debt"
    elif earned is not None and earned > DEPOSIT_YIELD_CEILING:
        kind = "unusual_income"
    elif cost is not None and material and cost < LOAN_COST_FLOOR:
        kind = "low_interest"
    else:
        kind = "carry" if material and spread is not None and spread > 0 else None
    return {**empty, "kind": kind, "fin_income": _s(income), "interest": _s(interest), "net": _s(income - interest), "avg_cash_like": _s(avg_cash),
            "avg_debt": _s(avg_debt), "yield": _r(earned), "cost": _r(cost), "spread": _r(spread)}


PROVISION_JUMP, PROVISION_MATERIAL = Decimal("0.50"), Decimal("0.01")


def _both(q: dict, st: str, lt: str) -> Decimal | None:
    a, b = _get(q, st, lt)
    return a + b if a is not None and b is not None else None


def _days(quarters: dict, period: str, stock: str, flow: str) -> Decimal | None:
    flows = [_get(quarters.get(_back(period, k), {}), flow)[0] for k in range(4)]
    (balance,) = _get(quarters.get(period, {}), stock)
    if balance is None or None in flows or sum(flows) <= 0:
        return None
    return (balance * 365 / sum(flows)).quantize(Decimal(1), ROUND_HALF_UP)  # multiplied first: no rounding before the halves


def _dso(quarters: dict, period: str) -> Decimal | None:
    return _days(quarters, period, "ar_customers", "revenue")


def _prepay_days(quarters: dict, period: str) -> Decimal | None:
    return _days(quarters, period, "prepay_suppliers", "cogs")


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    v, mid = sorted(values), len(values) // 2
    return v[mid] if len(v) % 2 else ((v[mid - 1] + v[mid]) / 2).quantize(Decimal(1), ROUND_HALF_UP)


def _days_view(quarters: dict, peers: dict | None, days_of) -> dict:
    latest = max(quarters) if quarters else None
    days = days_of(quarters, latest) if latest else None
    ago = days_of(quarters, _back(latest, 4)) if latest else None
    peer_days = [d for d in (days_of(qs, max(qs)) for qs in (peers or {}).values() if qs) if d is not None]
    return {"quarter": latest, "days": _s(days), "year_ago": _s(ago), "change": _s(days - ago) if days is not None and ago is not None else None,
            "sector_median": _s(_median(peer_days)), "sector_count": len(peer_days)}


RAISE_SHARE = Decimal("0.50")  # prepayments added against the charter capital a money-raising issue added


def _quarter_of(day: str) -> str:
    return f"{day[:4]}-Q{(int(day[5:7]) + 2) // 3}"


def raise_prepay(quarters: dict, share_issues: list[dict] | None) -> dict:
    """Each money-raising issue within the stored quarters: the quarter its capital was booked (that of the issue date, or the next), the
    capital added, prepayments to suppliers before it and at the quarter after, and whether they grew by half the capital or more."""
    events = []
    for day in sorted({i["date"] for i in (share_issues or []) if i.get("kind") == "raise" and i.get("date")}):
        q = _quarter_of(day)
        if q not in quarters:
            continue
        cap = lambda p: _get(quarters.get(p, {}), "charter_capital")[0]  # noqa: E731
        booked = next((p for p in (q, _back(q, -1)) if cap(p) is not None and cap(_back(p, 1)) is not None and cap(p) > cap(_back(p, 1))), None)
        if booked is None:
            continue
        after_q = _back(booked, -1) if _back(booked, -1) in quarters else booked
        added = cap(booked) - cap(_back(booked, 1))
        (before,), (after,) = _get(quarters.get(_back(booked, 1), {}), "prepay_suppliers"), _get(quarters.get(after_q, {}), "prepay_suppliers")
        grew = after - before if before is not None and after is not None else None
        events.append({"issue_date": day, "quarter": booked, "capital_added": _s(added), "prepay_before": _s(before), "prepay_after": _s(after),
                       "after_quarter": after_q, "prepay_added": _s(grew), "flag": grew is not None and grew >= RAISE_SHARE * added})
    return {"flag": any(e["flag"] for e in events), "events": events}


def _provision(q: dict) -> tuple[Decimal | None, Decimal | None]:
    """The short-term bad-debt provision as a positive amount, and its share of gross short-term receivables."""
    p, net = _get(q, "bad_debt_st", "receivables")
    if p is None:
        return None, None
    gross = (net or Decimal(0)) - p
    return -p, (-p / gross if net is not None and gross > 0 else None)


OTHER_HIGH, OTHER_FLOOR = Decimal(2), Decimal("0.05")  # twice the sector's median, and 5% of total assets


def _other_share(q: dict) -> Decimal | None:
    """Other receivables and loans (Thông tư 99 merges the two from 2026) against total assets; loan lines missing count as none."""
    other = _both(q, "other_receivables", "other_receivables_lt")
    (assets,) = _get(q, "total_assets")
    if other is None or not assets or assets <= 0:
        return None
    loans = sum((v for v in _get(q, "st_loans_receivable", "lt_loans_receivable") if v is not None), Decimal(0))
    return (other + loans) / assets


def _other_vs_sector(quarters: dict, peers: dict | None) -> dict:
    latest = max(quarters) if quarters else None
    share = _other_share(quarters[latest]) if latest else None
    peer = sorted(s for s in (_other_share(qs[max(qs)]) for qs in (peers or {}).values() if qs) if s is not None)
    median = None
    if peer:
        mid = len(peer) // 2
        median = peer[mid] if len(peer) % 2 else (peer[mid - 1] + peer[mid]) / 2
    high = None if share is None or median is None else share >= OTHER_FLOOR and share >= OTHER_HIGH * median
    return {"quarter": latest, "share": _r(share), "sector_median": _r(median), "sector_count": len(peer), "high": high}


def receivables_view(quarters: dict, peers: dict | None = None, n: int = 12) -> dict:
    """The last n quarters of receivables by part, the latest days to collect (with a year before and the sector's median over peers'
    latest quarters) and the latest provision. A missing line leaves its cell blank."""
    rows = []
    for period in sorted(quarters)[-n:]:
        q = quarters[period]
        total, other = _both(q, "receivables", "receivables_lt"), _both(q, "other_receivables", "other_receivables_lt")
        (assets,) = _get(q, "total_assets")
        share = lambda v: _r(v / assets) if v is not None and assets and assets > 0 else None  # noqa: E731
        provision = _both(q, "bad_debt_st", "bad_debt_lt")
        # the total is net of the provision (negative): before it and the share provided for (owner, 22/11/2026)
        gross = total - provision if total is not None and provision is not None else None
        rows.append({"quarter": period, "customers": _s(_both(q, "ar_customers", "ar_customers_lt")), "prepay": _s(_get(q, "prepay_suppliers")[0]),
                     "loans": _s(_both(q, "st_loans_receivable", "lt_loans_receivable")), "other": _s(other),
                     "provision": _s(provision), "total": _s(total), "gross": _s(gross),
                     "coverage": _r(-provision / gross) if gross is not None and gross > 0 else None, "total_share": share(total),
                     "other_share": share(other), "dso": _s(_dso(quarters, period)), "prepay_days": _s(_prepay_days(quarters, period))})
    latest = max(quarters) if quarters else None
    days = _dso(quarters, latest) if latest else None
    ago = _dso(quarters, _back(latest, 4)) if latest else None
    peer_days = sorted(d for d in (_dso(qs, max(qs)) for qs in (peers or {}).values() if qs) if d is not None)
    median = None
    if peer_days:
        mid = len(peer_days) // 2
        median = peer_days[mid] if len(peer_days) % 2 else ((peer_days[mid - 1] + peer_days[mid]) / 2).quantize(Decimal(1), ROUND_HALF_UP)
    amount, part = _provision(quarters[latest]) if latest else (None, None)
    before, _ = _provision(quarters.get(_back(latest, 4), {})) if latest else (None, None)
    kind = None
    if amount is not None and amount == 0:
        kind = "none"
    elif amount is not None and before is not None and before > 0 and amount / before - 1 >= PROVISION_JUMP and part is not None and part >= PROVISION_MATERIAL:
        kind = "jump"
    return {"rows": rows, "prepay_days": _days_view(quarters, peers, _prepay_days), "other_vs_sector": _other_vs_sector(quarters, peers),
            "dso": {"quarter": latest, "days": _s(days), "year_ago": _s(ago), "change": _s(days - ago) if days is not None and ago is not None else None,
                    "sector_median": _s(median), "sector_count": len(peer_days)},
            "provision": {"quarter": latest, "amount": _s(amount), "share": _r(part), "year_ago": _s(before), "kind": kind}}


LENDING_HIGH, LENDING_RISE = Decimal("0.30"), Decimal("0.10")  # Cho vay và phải thu khác so với vốn chủ (owner, 22/11/2026)


def _lent(q: dict, period: str) -> Decimal | None:
    """Loans receivable plus other receivables, short and long term. From 2026 Thông tư 99 folds loans into other receivables and drops
    the loans line: a missing loans line counts as nothing from then on, and leaves the cell blank before (never guessed)."""
    other = _both(q, "other_receivables", "other_receivables_lt")
    if other is None:
        return None
    st, lt = _get(q, "st_loans_receivable", "lt_loans_receivable")
    if st is None and lt is None:
        return other if int(period[:4]) >= 2026 else None
    return other + (st or Decimal(0)) + (lt or Decimal(0))


def lending_view(quarters: dict, n: int = 12) -> dict:
    """Cho vay và phải thu khác so với vốn chủ: each of the last n quarters, and a flag on the latest from 30%, or up 10 points on a year."""
    rows = []
    for period in sorted(quarters)[-n:]:
        lent, (equity,) = _lent(quarters[period], period), _get(quarters[period], "equity")
        share = lent / equity if lent is not None and equity is not None and equity > 0 else None
        rows.append({"quarter": period, "lent": _s(lent), "equity": _s(equity), "share": _r(share),
                     "equity_not_positive": equity is not None and equity <= 0})
    latest = max(quarters) if quarters else None
    flag = None
    if latest:
        now_row = next((r for r in rows if r["quarter"] == latest), None)
        ago_q = quarters.get(_back(latest, 4))
        ago = None
        if ago_q is not None:
            lent, (equity,) = _lent(ago_q, _back(latest, 4)), _get(ago_q, "equity")
            ago = lent / equity if lent is not None and equity is not None and equity > 0 else None
        share = Decimal(now_row["share"]) if now_row and now_row["share"] is not None else None
        if share is not None and share >= LENDING_HIGH:
            flag = "high"
        elif share is not None and ago is not None and share - ago >= LENDING_RISE:
            flag = "rising"
        return {"rows": rows, "quarter": latest, "share": _r(share), "year_ago": _r(ago), "flag": flag}
    return {"rows": rows, "quarter": None, "share": None, "year_ago": None, "flag": None}


RELEASE_SHARE = Decimal("0.20")  # Dự phòng đi vào lợi nhuận (owner, 22/11/2026)


def provision_flow(quarters: dict, n: int = 12) -> dict:
    """Dự phòng đi vào lợi nhuận: each quarter the change of the receivables provision balance (short and long term, as a positive
    amount) against that quarter's profit before tax. A fall from 20% of a positive profit is flagged; a fall can be a release (raising
    profit) or a write-off (not touching it), which public figures cannot tell apart."""
    rows = []
    for period in sorted(quarters)[-n:]:
        now_p, before_p = _both(quarters[period], "bad_debt_st", "bad_debt_lt"), _both(quarters.get(_back(period, 1), {}), "bad_debt_st", "bad_debt_lt")
        (pbt,) = _get(quarters[period], "pbt")
        change = (-now_p) - (-before_p) if now_p is not None and before_p is not None else None
        share = abs(change) / pbt if change is not None and pbt is not None and pbt > 0 else None
        rows.append({"quarter": period, "balance": _s(-now_p if now_p is not None else None), "change": _s(change), "pbt": _s(pbt), "share": _r(share),
                     "release": change is not None and change < 0 and share is not None and share >= RELEASE_SHARE})
    latest = rows[-1] if rows else None
    return {"rows": rows, "flag": bool(latest and latest["release"]), "quarter": latest["quarter"] if latest else None}


def inventory_view(quarters: dict, n: int = 12) -> dict:
    """Khối Tồn kho (owner, 22/11/2026): each of the last n quarters at cost, the provision for a fall in value (as a positive amount), net,
    the share provided for and net inventory against total assets. A line not fetched leaves its cell blank; cost is never worked back."""
    rows = []
    for period in sorted(quarters)[-n:]:
        gross, provision, net, assets = _get(quarters[period], "inventory_gross", "inventory_provision", "inventory", "total_assets")
        rows.append({"quarter": period, "gross": _s(gross), "provision": _s(-provision if provision is not None else None), "net": _s(net),
                     "coverage": _r(-provision / gross) if provision is not None and gross is not None and gross > 0 else None,
                     "share": _r(net / assets) if net is not None and assets is not None and assets > 0 else None})
    return {"rows": rows}


def _advances(q: dict) -> Decimal | None:
    st, lt = _get(q, "advances_st", "advances_lt")
    return st + lt if st is not None and lt is not None else None


def property_cash(quarters: dict, n: int = 12) -> dict:
    """A property developer's last n quarters (customer advances, inventory, cash from operations, parent profit) and the reading of
    the latest quarter against the same quarter a year before."""
    periods = sorted(quarters)[-n:]
    rows = [{"quarter": p, "advances": _s(_advances(quarters[p])), "inventory": _s(_get(quarters[p], "inventory")[0]),
             "cfo": _s(_get(quarters[p], "cfo")[0]), "npat_parent": _s(_get(quarters[p], "npat_parent")[0])} for p in periods]
    signal = {"kind": None, "quarter": None, "advances_yoy": None, "profit_yoy": None}
    if periods:
        last = periods[-1]
        ago = quarters.get(_back(last, 4), {})
        adv, adv_ago = _advances(quarters[last]), _advances(ago)
        (profit,), (profit_ago,) = _get(quarters[last], "npat_parent"), _get(ago, "npat_parent")
        adv_yoy = adv / adv_ago - 1 if adv is not None and adv_ago is not None and adv_ago > 0 else None
        profit_yoy = profit / profit_ago - 1 if profit is not None and profit_ago is not None and profit_ago > 0 else None
        jumped = (profit_yoy is not None and profit_yoy >= HANDOVER_PROFIT) or (profit is not None and profit_ago is not None and profit_ago <= 0 < profit)
        kind = None
        if adv_yoy is not None and adv_yoy <= HANDOVER_ADVANCES and jumped:
            kind = "handover"
        elif adv_yoy is not None and adv_yoy >= COLLECTING_ADVANCES:
            kind = "collecting"
        signal = {"kind": kind, "quarter": last, "advances_yoy": _r(adv_yoy), "profit_yoy": _r(profit_yoy)}
    return {"rows": rows, "signal": signal}
