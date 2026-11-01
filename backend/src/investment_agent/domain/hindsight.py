"""Hậu kiểm quyết định: how the owner's past decisions turned out, from the ledger, stored closes, the Nhật ký and the theses.

Every figure is something that already happened; a horizon not reached yet is "not_yet" and a missing price is "missing", never
filled. Groups under five observations are reported as not enough to conclude. Personal data, computed on the owner's machine."""

import calendar
from bisect import bisect_right
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from investment_agent.domain.ledger import OpeningBalance, Trade, ordered_events, replay

HORIZONS = (3, 6, 12)
MIN_OBSERVATIONS = 5
CHASE_SESSIONS, CHASE_RISE = 20, Decimal("0.15")
LINK_DAYS = 30  # a thesis written within a month after a buy explains that buy


def _r(value: Decimal | None) -> str | None:
    return None if value is None else format(value.quantize(Decimal("0.0001"), ROUND_HALF_UP), "f")


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return d.replace(year=year, month=month, day=min(d.day, calendar.monthrange(year, month)[1]))


class _Series:
    """Closes on or before a day (thousand đồng for stocks; given back in đồng), only up to today and only real prices."""

    def __init__(self, points, today: date, scale: int):
        kept = sorted((d, Decimal(str(v)) * scale) for d, v in points if d <= today and v > 0)
        self.days, self.values = [d for d, _ in kept], [v for _, v in kept]

    def on(self, d: date) -> tuple[date, Decimal] | None:
        i = bisect_right(self.days, d)
        return (self.days[i - 1], self.values[i - 1]) if i else None

    def index_of(self, d: date) -> int | None:
        i = bisect_right(self.days, d)
        return i - 1 if i else None


class _Book:
    """Ledger state after each event day, to read a position's shares and average cost on any day."""

    def __init__(self, events):
        self.events = ordered_events(list(events))
        self.days, self.states = [], []
        for i, e in enumerate(self.events):
            if i + 1 < len(self.events) and self.events[i + 1].effective_at == e.effective_at:
                continue
            self.days.append(e.effective_at)
            self.states.append({p.security_id: (p.quantity + p.pending_quantity, p.average_cost) for p in replay(self.events[:i + 1]).positions})

    def at(self, d: date, *, before: bool = False) -> dict:
        i = bisect_right(self.days, d - timedelta(days=1) if before else d)
        return self.states[i - 1] if i else {}


def _horizon(series: _Series | None, index: _Series, start: date, base: Decimal, months: int, today: date) -> dict:
    on = _add_months(start, months)
    empty = {"on": on.isoformat(), "change": None, "index": None, "diff": None}
    if on > today:
        return {"status": "not_yet", **empty}
    got = series.on(on) if series else None
    if got is None:
        return {"status": "missing", **empty}
    change = got[1] / base - 1
    i0, i1 = index.on(start), index.on(on)
    idx = i1[1] / i0[1] - 1 if i0 and i1 else None
    return {"status": "ok", "on": on.isoformat(), "change": _r(change), "index": _r(idx), "diff": _r(None if idx is None else change - idx)}


def _loss_holds(symbol: str, book: _Book, series: _Series, sells: dict, threshold: Decimal) -> list[dict]:
    out, period = [], None
    days = sorted(set(series.days) | {d for d, s in sells if s == symbol})
    for d in days:
        qty, cost = book.at(d).get(symbol, (0, Decimal(0)))
        if period and qty == 0:
            sale = sells.get((d, symbol))
            before = book.at(d, before=True).get(symbol, (0, Decimal(0)))[1]
            period.update(end=d, outcome="sold_at_loss" if sale is not None and sale < before else "recovered")
            out.append(period)
            period = None
            continue
        close = series.on(d)
        if qty == 0 or not cost or close is None or close[0] != d:
            continue
        ratio = close[1] / cost - 1
        if period is None and ratio <= -threshold:
            period = {"start": d, "deepest": ratio}
        elif period is not None:
            period["deepest"] = min(period["deepest"], ratio)
            if ratio >= 0:
                period.update(end=d, outcome="recovered")
                out.append(period)
                period = None
    if period:
        period.update(end=None, outcome="holding")
        out.append(period)
    return [{"symbol": symbol, "start": p["start"].isoformat(), "end": None if p["end"] is None else p["end"].isoformat(),
             "days": None if p["end"] is None else (p["end"] - p["start"]).days, "deepest": _r(p["deepest"]), "outcome": p["outcome"]}
            for p in out]


def _group(rows: list[tuple[str, dict]]) -> list[dict]:
    """Six-month results per key; under five observations no mean is given."""
    by: dict[str, list[dict]] = {}
    for key, h in rows:
        if h["status"] == "ok":
            by.setdefault(key, []).append(h)
    out = []
    for key, hs in sorted(by.items()):
        enough = len(hs) >= MIN_OBSERVATIONS
        diffs = [Decimal(h["diff"]) for h in hs if h["diff"] is not None]
        out.append({"key": key, "count": len(hs), "enough": enough,
                    "mean": _r(sum(Decimal(h["change"]) for h in hs) / len(hs)) if enough else None,
                    "mean_diff": _r(sum(diffs) / len(diffs)) if enough and diffs else None})
    return out


def hindsight(events, *, closes: dict, index: list, journal: list[dict], theses: list[dict], threshold: Decimal, today: date) -> dict:
    events = list(events)
    book = _Book(events)
    series = {s: _Series(p, today, 1000) for s, p in closes.items()}
    idx = _Series(index, today, 1)
    trades = [e for e in book.events if isinstance(e, Trade)]
    opening = sum(len(e.positions) for e in book.events if isinstance(e, OpeningBalance))
    sells = {(e.effective_at, e.security_id): e.price for e in trades if e.type == "sell"}

    rows = []
    for e in trades:
        s = series.get(e.security_id)
        rows.append({"event_id": e.event_id, "symbol": e.security_id, "type": e.type, "date": e.effective_at.isoformat(),
                     "price": format(e.price.normalize(), "f"), "quantity": e.quantity,
                     "horizons": {str(m): _horizon(s, idx, e.effective_at, e.price, m, today) for m in HORIZONS}})

    loss_holds = []
    for symbol in sorted({e.security_id for e in trades}):
        if symbol in series:
            loss_holds += _loss_holds(symbol, book, series[symbol], sells, threshold)

    breaks, seen = [], set()
    for t in theses:
        found = [(h.get("condition"), h["kind"], h["broken_on"], h["broken_price"], True) for h in t.get("history", []) if h.get("type") == "hold"]
        found += [(c.get("id"), c["kind"], c["broken_on"], c["broken_price"], c.get("hold") is not None) for c in t["conditions"]
                  if c.get("status") == "broken"]
        for cid, kind, on, price, held in found:
            if not on or not price or (cid, on) in seen:
                continue
            seen.add((cid, on))
            start = date.fromisoformat(on)
            sale = next(((d, p) for d, p in sorted((d, p) for (d, s), p in sells.items() if s == t["symbol"])
                         if d >= start and book.at(d).get(t["symbol"], (0, 0))[0] == 0), None)
            last = series[t["symbol"]].on(today) if t["symbol"] in series else None
            then_on, then, how = (sale[0], sale[1], "sold") if sale else (last[0], last[1], "holding") if last else (None, None, "missing")
            breaks.append({"symbol": t["symbol"], "kind": kind, "broken_on": on, "broken_price": price, "held_on": held,
                           "then": None if then is None else format(then.normalize(), "f"), "then_on": None if then_on is None else then_on.isoformat(),
                           "how": how, "change": _r(None if then is None else then / Decimal(price) - 1)})
    breaks.sort(key=lambda b: (b["broken_on"], b["symbol"]))

    sell_days = sorted({d for d, _ in sells})
    rg = rl = pg = pl = 0
    for d in sell_days:
        for symbol, (qty, cost) in book.at(d, before=True).items():
            if qty <= 0 or not cost:
                continue
            sold = sells.get((d, symbol))
            close = series[symbol].on(d) if symbol in series else None
            price = sold if sold is not None else close[1] if close else None
            if price is None or price == cost:
                continue
            gain = price > cost
            if sold is not None:
                rg, rl = rg + gain, rl + (not gain)
            else:
                pg, pl = pg + gain, pl + (not gain)
    enough = len(sell_days) >= MIN_OBSERVATIONS
    disposition = {"days": len(sell_days), "pgr": _r(Decimal(rg) / (rg + pg)) if enough and rg + pg else None,
                   "plr": _r(Decimal(rl) / (rl + pl)) if enough and rl + pl else None, "enough": enough}

    emotions = {j["ledger_event_id"]: j["emotion"] for j in journal if j.get("ledger_event_id") and j.get("emotion")}
    buys = [r for r in rows if r["type"] == "buy"]
    by_emotion = _group([(emotions[r["event_id"]], r["horizons"]["6"]) for r in buys if r["event_id"] in emotions])
    reason_rows = []
    for r in buys:
        d = date.fromisoformat(r["date"])
        for t in theses:
            created = date.fromisoformat(t["created_on"]) if t.get("created_on") else None
            closed = date.fromisoformat(t["closed_on"]) if t.get("closed_on") else None
            if t["symbol"] == r["symbol"] and created and created <= d + timedelta(days=LINK_DAYS) and (closed is None or closed >= d):
                reason_rows += [(reason, r["horizons"]["6"]) for reason in t.get("reasons", [])]
                break
    chase, other = [], []
    for r in buys:
        s = series.get(r["symbol"])
        i = s.index_of(date.fromisoformat(r["date"])) if s else None
        if i is None or i < CHASE_SESSIONS:
            continue
        (chase if s.values[i] / s.values[i - CHASE_SESSIONS] - 1 > CHASE_RISE else other).append(("x", r["horizons"]["6"]))
    empty = {"key": "x", "count": 0, "enough": False, "mean": None, "mean_diff": None}
    return {"trades": rows, "opening_skipped": opening, "loss_holds": loss_holds, "breaks": breaks,
            "biases": {"disposition": disposition, "by_emotion": by_emotion, "by_reason": _group(reason_rows),
                       "chasing": {"chasing": (_group(chase) or [empty])[0], "other": (_group(other) or [empty])[0]}}}
