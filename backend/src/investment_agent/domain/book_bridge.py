"""Sổ tài sản's part of the month waterfall: the book as last saved by the end of each day, valued as Sổ tài sản values it (a fund
at units × NAV, gold at chỉ × the buying price, every other row at what was entered), and the change split into

- book:fund_price: the units held at the start × the change in NAV, for a fund row kept through the month;
- book:gold_price: the chỉ held at the start × the change in buying price, for a gold row kept through the month;
- book:entries: everything else (rows added, removed or edited: deposits, cash accounts, crypto, units bought or sold).

Prices are the latest kept on or before the day, no older than the staleness Sổ tài sản allows (NAV 14 days, gold 3). A fund or gold
kind that has a price history but none for a day stops this part, named: its value that day is unknown. One never priced is at cost
on both days, as Sổ tài sản counts it.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .deposit_book import GOLD_STALE_DAYS, NAV_STALE_DAYS, DepositBook


def _price(history: dict[str, str] | None, day: date, stale: int) -> Decimal | None:
    if not history:
        return None
    known = [d for d in history if date.fromisoformat(d) <= day and date.fromisoformat(d) >= day - timedelta(days=stale)]
    return Decimal(history[max(known)]) if known else None


def _value(book: DepositBook | None, navs: dict, gold: dict, day: date, missing: set) -> tuple[Decimal, dict, dict]:
    """Total, {fund row id: (fund, units, nav)}, {gold row id: (kind, chi, price)} of the rows priced on the day."""
    if book is None:
        return Decimal(0), {}, {}
    total = sum((a.amount for a in book.accounts), Decimal(0)) + sum((d.principal for d in book.deposits), Decimal(0))
    total += sum((c.amount for c in book.crypto), Decimal(0))
    funds, golds = {}, {}
    for b in book.bonds:
        nav = _price(navs.get(b.fund), day, NAV_STALE_DAYS) if b.fund else None
        if nav is not None:
            total += (b.units * nav).quantize(Decimal(1), ROUND_HALF_UP)
            funds[b.id] = (b.fund, b.units, nav)
        elif b.fund and navs.get(b.fund):
            missing.add(b.fund)
        else:
            total += b.amount
    for g in book.gold:
        price = _price(gold.get(g.kind), day, GOLD_STALE_DAYS) if g.kind else None
        if price is not None:
            total += (g.chi * price).quantize(Decimal(1), ROUND_HALF_UP)
            golds[g.id] = (g.kind, g.chi, price)
        elif g.kind and gold.get(g.kind):
            missing.add(g.kind)
        else:
            total += g.amount
    return total, funds, golds


def _s(v: Decimal) -> str:
    q = v.quantize(Decimal(1), ROUND_HALF_UP)
    return format(q, "f") if q != 0 else "0"


def book_bridge(start_book: DepositBook | None, end_book: DepositBook | None, *, navs: dict, gold: dict, start_day: date | None, end_day: date) -> dict:
    """navs: market.fund_nav.fund_history(); gold: market.gold_price.gold_history()."""
    missing: set = set()
    v_start, f_start, g_start = _value(start_book, navs, gold, start_day, missing) if start_day else (Decimal(0), {}, {})
    v_end, f_end, g_end = _value(end_book, navs, gold, end_day, missing)
    if missing:
        return {"status": "missing_prices", "missing": sorted(missing), "start_day": start_day.isoformat() if start_day else None,
                "end_day": end_day.isoformat()}
    fund_price = sum(((f_end[i][2] - nav) * units for i, (fund, units, nav) in f_start.items() if i in f_end and f_end[i][0] == fund), Decimal(0))
    gold_price = sum(((g_end[i][2] - p) * chi for i, (kind, chi, p) in g_start.items() if i in g_end and g_end[i][0] == kind), Decimal(0))
    fund_price, gold_price = fund_price.quantize(Decimal(1), ROUND_HALF_UP), gold_price.quantize(Decimal(1), ROUND_HALF_UP)
    entries = v_end - v_start - fund_price - gold_price  # the steps add up to the change exactly
    steps = [{"id": "book:fund_price", "amount": _s(fund_price)}, {"id": "book:gold_price", "amount": _s(gold_price)},
             {"id": "book:entries", "amount": _s(entries)}]
    return {"status": "ok", "start": _s(v_start), "end": _s(v_end), "steps": [s for s in steps if s["amount"] != "0"]}
