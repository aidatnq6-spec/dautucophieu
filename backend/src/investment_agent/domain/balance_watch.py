"""Nợ vay ròng and Tiền khách trả trước: two readings of a non-financial company's balance sheet, from its public statements.

Net debt = short- and long-term borrowing − cash − short-term investments; below zero the company holds more cash than it owes
banks (net cash). Borrowing that at least doubled in two years is flagged when it is a material part of the balance sheet. A
sector adds up its tickers' borrowing each quarter. For a property developer, money customers paid ahead (người mua trả tiền
trước, short and long term) against the same quarter a year before: profit jumping while those advances fall reads as handing
over homes already paid for; advances rising reads as money collected for homes still to be handed over. A missing line leaves
its figure blank; nothing is filled in. Readings, not advice."""

from decimal import ROUND_HALF_UP, Decimal

_Q4 = Decimal("0.0001")
FAST_BORROWING = Decimal(2)  # borrowing at least twice what it was eight quarters before
MATERIAL_DEBT = Decimal("0.05")  # ... and at least 5% of total assets, so a tiny loan doubling is not flagged
HANDOVER_ADVANCES = Decimal("-0.10")  # advances down 10% or more against a year before
HANDOVER_PROFIT = Decimal("0.50")  # while the quarter's parent profit is up 50% or more (or turned from a loss)
COLLECTING_ADVANCES = Decimal("0.20")  # advances up 20% or more against a year before


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
