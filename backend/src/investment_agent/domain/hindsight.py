"""Hậu kiểm quyết định: how the owner's past decisions turned out, from the ledger, stored closes, the Nhật ký and the theses.

Every figure is something that already happened; a horizon not reached yet is "not_yet" and a missing or stale price is "missing"
with the reason, never filled. Stored closes are adjusted for later dividends and issues (Vnstock), so a close is only ever
compared with another close of the same series: price moves run close to close, and the cost a close is held against is the
average of the adjusted closes on the buy days. Groups under five matured observations are not concluded. Personal data,
computed on the owner's machine."""

import calendar
from bisect import bisect_right
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from investment_agent.domain.ledger import OpeningBalance, Trade, ordered_events, snapshots
from investment_agent.domain.thesis import KINDS

HORIZONS = (3, 6, 12)
MIN_OBSERVATIONS = 5
CHASE_SESSIONS, CHASE_RISE = 20, Decimal("0.15")
LINK_DAYS = 30  # a thesis written within a month after a buy explains that buy
FRESH_DAYS = 7  # a close older than this before the day asked for is not that day's price


def _r(value: Decimal | None) -> str | None:
    return None if value is None else format(value.quantize(Decimal("0.0001"), ROUND_HALF_UP), "f")


def _dmy(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return d.replace(year=year, month=month, day=min(d.day, calendar.monthrange(year, month)[1]))


class _Series:
    """Stored closes up to today (thousand đồng for stocks, given back in đồng). on() is the close of that day or of a session
    shortly before; an older close is no price for that day."""

    def __init__(self, points, today: date, scale: int):
        kept = sorted((d, Decimal(str(v)) * scale) for d, v in points if d <= today and v > 0)
        self.days, self.values = [d for d, _ in kept], [v for _, v in kept]

    def _at(self, d: date) -> int | None:
        i = bisect_right(self.days, d)
        return i - 1 if i else None

    def on(self, d: date) -> tuple[date, Decimal] | None:
        i = self._at(d)
        return (self.days[i], self.values[i]) if i is not None and (d - self.days[i]).days <= FRESH_DAYS else None

    def index_on(self, d: date) -> int | None:
        i = self._at(d)
        return i if i is not None and (d - self.days[i]).days <= FRESH_DAYS else None

    def why(self, d: date) -> str:
        if not self.days:
            return "Chưa có giá đã lưu của mã"
        i = self._at(d)
        return "Chưa có giá đã lưu tại ngày này" if i is None else f"Giá đã lưu chỉ tới {_dmy(self.days[i])}"


EMPTY = _Series([], date.min, 1)


class _Book:
    """Ledger state after each event day (shares including pending, average cost in đồng), and the average adjusted close of the
    buys still held (đồng per share, comparable with stored closes; None when a buy day has no close)."""

    def __init__(self, events, series: dict):
        self.events = ordered_events(list(events))
        self.days, self.states, self.adjusted = [], [], []
        adj: dict[str, Decimal | None] = {}
        previous: dict = {}
        for i, (e, snap) in enumerate(snapshots(self.events)):
            if isinstance(e, Trade) and e.type == "buy":
                close = series.get(e.security_id, EMPTY).on(e.effective_at)
                q0 = sum(previous.get(e.security_id, (0, 0, 0))[:2])
                old = adj.get(e.security_id)
                adj[e.security_id] = None if close is None or (q0 and old is None) else (old * q0 + close[1] * e.quantity) / (q0 + e.quantity) if q0 else close[1]
            elif isinstance(e, OpeningBalance):
                for p in e.positions:
                    close = series.get(p.security_id, EMPTY).on(e.effective_at)
                    adj[p.security_id] = close[1] if close else None
            previous = snap
            if i + 1 < len(self.events) and self.events[i + 1].effective_at == e.effective_at:
                continue
            state = {s: (q + pending, cost) for s, (q, pending, cost) in snap.items()}
            for s in list(adj):
                if state.get(s, (0, 0))[0] <= 0:
                    adj.pop(s)
            self.days.append(e.effective_at)
            self.states.append(state)
            self.adjusted.append(dict(adj))

    def _i(self, d: date, before: bool) -> int | None:
        i = bisect_right(self.days, d - timedelta(days=1) if before else d)
        return i - 1 if i else None

    def at(self, d: date, *, before: bool = False) -> dict:
        i = self._i(d, before)
        return self.states[i] if i is not None else {}

    def adjusted_cost(self, symbol: str, d: date, *, before: bool = False) -> Decimal | None:
        i = self._i(d, before)
        return self.adjusted[i].get(symbol) if i is not None else None


def _horizon(series: _Series, index: _Series, start: date, months: int, today: date) -> dict:
    on = _add_months(start, months)
    empty = {"on": on.isoformat(), "change": None, "index": None, "diff": None, "reason": None}
    if on > today or (on == today and (not series.days or series.days[-1] < today)):  # today's close comes with the 20:00 run
        return {"status": "not_yet", **empty}
    base, got = series.on(start), series.on(on)
    if base is None or got is None:
        return {"status": "missing", **empty, "reason": series.why(start if base is None else on)}
    change = got[1] / base[1] - 1
    i0, i1 = index.on(start), index.on(on)
    idx = i1[1] / i0[1] - 1 if i0 and i1 else None
    return {"status": "ok", "on": on.isoformat(), "change": _r(change), "index": _r(idx), "diff": _r(None if idx is None else change - idx),
            "reason": None}


def _weighted(trades: list[tuple[int, Decimal]]) -> Decimal:
    return sum(q * p for q, p in trades) / sum(q for q, _ in trades)


def _loss_holds(symbol: str, book: _Book, series: _Series, sells: dict, buys: set, threshold: Decimal) -> list[dict]:
    out, period = [], None
    days = sorted(set(series.days) | {d for d, s in sells if s == symbol} | {d for d, s in buys if s == symbol})
    for d in days:
        qty = book.at(d).get(symbol, (0, Decimal(0)))[0]
        if period and qty == 0:
            sale = sells.get((d, symbol))
            before = book.at(d, before=True).get(symbol, (0, Decimal(0)))[1]
            period.update(end=d, outcome="sold_at_loss" if sale and _weighted(sale) < before else "recovered")
            out.append(period)
            period = None
            continue
        if period and (d, symbol) in buys:  # buying more lowers the cost: the period ends without the price coming back
            period.update(end=d, outcome="averaged_down")
            out.append(period)
            period = None
            continue
        cost, close = book.adjusted_cost(symbol, d), series.on(d)
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


def _group(rows: list[tuple[str, dict]], keys: tuple[str, ...] = ()) -> list[dict]:
    """Six-month results per key: every observation counted, the mean only from five that have reached six months."""
    by: dict[str, list[dict]] = {k: [] for k in keys}
    for key, h in rows:
        by.setdefault(key, []).append(h)
    out = []
    for key, hs in sorted(by.items()):
        ok = [h for h in hs if h["status"] == "ok"]
        enough = len(ok) >= MIN_OBSERVATIONS
        diffs = [Decimal(h["diff"]) for h in ok if h["diff"] is not None]
        out.append({"key": key, "count": len(hs), "matured": len(ok), "enough": enough,
                    "mean": _r(sum(Decimal(h["change"]) for h in ok) / len(ok)) if enough else None,
                    "mean_diff": _r(sum(diffs) / len(diffs)) if enough and diffs else None})
    return out


def _chasing(bought: list[dict], series: dict) -> dict:
    """Buys after the price had risen more than CHASE_RISE in CHASE_SESSIONS, against the other buys."""
    rows = []
    for r in bought:
        s = series.get(r["symbol"], EMPTY)
        i = s.index_on(date.fromisoformat(r["date"]) - timedelta(days=1))  # the sessions before the buy day
        if i is None or i < CHASE_SESSIONS:
            continue
        rows.append(("chasing" if s.values[i] / s.values[i - CHASE_SESSIONS] - 1 > CHASE_RISE else "other", r["horizons"]["6"]))
    return {g["key"]: g for g in _group(rows, ("chasing", "other"))}


def imported_hindsight(rows: list[dict], *, closes: dict, index: list, today: date) -> dict:
    """Stock orders brought in from an older journal, kept apart from the ledger's: no fees or taxes, and no holdings to rebuild, so the
    measures that need a position (Odean's ratios, losses held) are not computed. Each order is followed close to close on the adjusted
    series, as the ledger's are. A sale counts as made at a gain or a loss by the profit typed with it; a typed 0 tells nothing (the
    old page saved a blank as 0) and is left out."""
    series = {s: _Series(p, today, 1000) for s, p in closes.items()}
    idx = _Series(index, today, 1)
    trades = [{"entry_id": r["entry_id"], "symbol": r["symbol"], "type": r["kind"], "date": r["date"].isoformat(), "price": r["price"], "quantity": r["qty"],
               "horizons": {str(m): _horizon(series.get(r["symbol"], EMPTY), idx, r["date"], m, today) for m in HORIZONS}} for r in rows]
    typed = {r["entry_id"]: Decimal(r["pnl"]) for r in rows if r.get("pnl") not in (None, "") and Decimal(r["pnl"]) != 0}
    sold = _group([("gain" if typed[t["entry_id"]] > 0 else "loss", t["horizons"]["6"]) for t in trades if t["type"] == "sell" and t["entry_id"] in typed], ("gain", "loss"))
    trades.sort(key=lambda t: t["date"], reverse=True)
    return {"trades": trades, "count": len(trades), "measured": sum(1 for t in trades if any(h["status"] == "ok" for h in t["horizons"].values())),
            "missing_symbols": sorted({r["symbol"] for r in rows if not series.get(r["symbol"], EMPTY).days}),
            "biases": {"chasing": _chasing([t for t in trades if t["type"] == "buy"], series), "sold": {g["key"]: g for g in sold}}}


def hindsight(events, *, closes: dict, index: list, journal: list[dict], theses: list[dict], threshold: Decimal, today: date) -> dict:
    series = {s: _Series(p, today, 1000) for s, p in closes.items()}
    book = _Book(list(events), series)
    idx = _Series(index, today, 1)
    trades = [e for e in book.events if isinstance(e, Trade)]
    opening = sum(len(e.positions) for e in book.events if isinstance(e, OpeningBalance))
    sells: dict[tuple[date, str], list[tuple[int, Decimal]]] = {}
    for e in trades:
        if e.type == "sell":
            sells.setdefault((e.effective_at, e.security_id), []).append((e.quantity, e.price))
    buys = {(e.effective_at, e.security_id) for e in trades if e.type == "buy"}

    rows = [{"event_id": e.event_id, "symbol": e.security_id, "type": e.type, "date": e.effective_at.isoformat(),
             "price": format(e.price.normalize(), "f"), "quantity": e.quantity,
             "horizons": {str(m): _horizon(series.get(e.security_id, EMPTY), idx, e.effective_at, m, today) for m in HORIZONS}}
            for e in trades]

    loss_holds = []
    for symbol in sorted({e.security_id for e in trades} | {p.security_id for e in book.events if isinstance(e, OpeningBalance) for p in e.positions}):
        if symbol in series:
            loss_holds += _loss_holds(symbol, book, series[symbol], sells, buys, threshold)

    breaks, seen = [], set()
    for t in theses:
        found = [(h.get("condition"), h["kind"], h["broken_on"], h["broken_price"], True) for h in t.get("history", []) if h.get("type") == "hold"]
        found += [(c.get("id"), c["kind"], c["broken_on"], c["broken_price"], c.get("hold") is not None) for c in t["conditions"]
                  if c.get("status") == "broken"]
        closed = date.fromisoformat(t["closed_on"]) if t.get("closed_on") else None
        for cid, kind, on, price, held in found:
            if not on or not price or Decimal(price) <= 0 or (cid, kind, on) in seen:
                continue
            seen.add((cid, kind, on))
            start = date.fromisoformat(on)
            exits = sorted((d, _weighted(p)) for (d, s), p in sells.items() if s == t["symbol"] and d >= start and (closed is None or d <= closed)
                           and book.at(d).get(t["symbol"], (0, 0))[0] == 0)
            last = series.get(t["symbol"], EMPTY).on(today) if closed is None else None
            then_on, then, how = exits[0] + ("sold",) if exits else (last[0], last[1], "holding") if last else (None, None, "missing")
            breaks.append({"symbol": t["symbol"], "kind": kind, "label": KINDS[kind][0] if kind in KINDS else kind, "broken_on": on,
                           "broken_price": price, "held_on": held, "then": None if then is None else format(then.normalize(), "f"),
                           "then_on": None if then_on is None else then_on.isoformat(), "how": how,
                           "change": _r(None if then is None else then / Decimal(price) - 1)})
    breaks.sort(key=lambda b: (b["broken_on"], b["symbol"]))

    sell_days = sorted({d for d, _ in sells})
    rg = rl = pg = pl = 0
    for d in sell_days:
        for symbol, (qty, cost) in book.at(d, before=True).items():
            if qty <= 0:
                continue
            sold = sells.get((d, symbol))
            if sold is not None:  # realised: the sale against the ledger's cost, both as traded
                price, base = _weighted(sold), cost
            else:  # still held: the day's adjusted close against the adjusted cost of the buys
                close, base = series.get(symbol, EMPTY).on(d), book.adjusted_cost(symbol, d, before=True)
                price = close[1] if close else None
            if price is None or not base or price == base:
                continue
            gain = price > base
            if sold is not None:
                rg, rl = rg + gain, rl + (not gain)
            else:
                pg, pl = pg + gain, pl + (not gain)
    enough = len(sell_days) >= MIN_OBSERVATIONS
    disposition = {"days": len(sell_days), "pgr": _r(Decimal(rg) / (rg + pg)) if enough and rg + pg else None,
                   "plr": _r(Decimal(rl) / (rl + pl)) if enough and rl + pl else None, "enough": enough}

    emotions = {j["ledger_event_id"]: j["emotion"] for j in journal if j.get("ledger_event_id") and j.get("emotion")}
    bought = [r for r in rows if r["type"] == "buy"]
    by_emotion = _group([(emotions[r["event_id"]], r["horizons"]["6"]) for r in bought if r["event_id"] in emotions])
    reason_rows = []
    for r in bought:
        d = date.fromisoformat(r["date"])
        for t in theses:
            created = date.fromisoformat(t["created_on"]) if t.get("created_on") else None
            closed = date.fromisoformat(t["closed_on"]) if t.get("closed_on") else None
            if t["symbol"] == r["symbol"] and created and created <= d + timedelta(days=LINK_DAYS) and (closed is None or closed >= d):
                reason_rows += [(reason, r["horizons"]["6"]) for reason in t.get("reasons", [])]
                break
    chasing = _chasing(bought, series)
    return {"trades": rows, "opening_skipped": opening, "loss_holds": loss_holds, "breaks": breaks,
            "biases": {"disposition": disposition, "by_emotion": by_emotion, "by_reason": _group(reason_rows), "chasing": chasing}}


def lesson(breaks: list[dict]) -> str | None:
    """The owner's own record of holding on after a broken condition, for the thesis note; None under five times."""
    held = [Decimal(b["change"]) for b in breaks if b.get("held_on") and b.get("change") is not None]
    if len(held) < MIN_OBSERVATIONS:
        return None
    mean = sum(held) / len(held) * 100
    sign = "−" if mean < 0 else "+" if mean > 0 else ""
    text = f"{abs(mean).quantize(Decimal('0.1'), ROUND_HALF_UP)}".replace(".", ",")
    return (f"{len(held)} lần trước bạn giữ tiếp sau khi điều kiện bị phá; so với bán ngay lúc báo đầu, trung bình {sign}{text}% "
            "(đã xảy ra, không phải dự báo).")
