"""Lãi đã trả lại thị trường and Mục tiêu đã đủ tiền: the highest gain each holding has had in its current holding period, today's gain,
and how much of it went back; and whether the owner's spending goals are covered. Personal data, computed on the owner's machine.

Stored closes are adjusted for later dividends and issues, so a day's close is only compared with the adjusted cost (the average of the
adjusted closes on the buy days still held), as Hậu kiểm does: gain on day d = (close / adjusted cost − 1) × the real cost held that day.
The figure therefore counts dividends and bonus shares received, and may differ from the ledger's unrealised gain. Only sessions with a
close that very day count; nothing is filled."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from investment_agent.domain.hindsight import _Book, _Series

_Q4, _Q0 = Decimal("0.0001"), Decimal("1")


def _r(value: Decimal) -> str:
    return format(value.quantize(_Q4, ROUND_HALF_UP), "f")


def _d(value: Decimal) -> str:
    return format(value.quantize(_Q0, ROUND_HALF_UP), "f")


def _dmy(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _summary(points: list[tuple[date, Decimal, Decimal]]) -> dict:
    """points: (day, gain, cost) in order. The peak is the first day of the highest gain; a peak not above zero is no peak."""
    if not points:
        return {"peak": None, "now": None, "given_back": None, "share": None, "sessions_since_peak": None, "never_gained": False}
    view = lambda p: {"gain": _d(p[1]), "ratio": _r(p[1] / p[2]) if p[2] else None, "on": p[0].isoformat()}  # noqa: E731
    i = max(range(len(points)), key=lambda k: (points[k][1], -k))
    now = points[-1]
    if points[i][1] <= 0:
        return {"peak": None, "now": view(now), "given_back": None, "share": None, "sessions_since_peak": None, "never_gained": True}
    back = points[i][1] - now[1]
    return {"peak": view(points[i]), "now": view(now), "given_back": _d(back), "share": _r(back / points[i][1]),
            "sessions_since_peak": len(points) - 1 - i, "never_gained": False}


def _period_start(book: _Book, symbol: str) -> date | None:
    start, before = None, 0
    for day, state in zip(book.days, book.states):
        qty = state.get(symbol, (0, 0))[0]
        if qty > 0 and before <= 0:
            start = day
        before = qty
    return start if before > 0 else None


def _holding(symbol: str, book: _Book, series: _Series, today: date) -> tuple[dict, list[tuple[date, Decimal, Decimal]]]:
    since = _period_start(book, symbol)
    row = {"symbol": symbol, "since": since.isoformat(), "reason": None}
    if not series.days:
        return {**row, **_summary([]), "reason": "Chưa có giá đã lưu của mã", "days": []}, []
    missing = next((d for d in book.days if since <= d <= today and book.at(d).get(symbol, (0, 0))[0] > 0
                    and book.adjusted_cost(symbol, d) is None), None)
    if missing is not None:
        return {**row, **_summary([]), "reason": f"Chưa có giá đã lưu tại ngày mua {_dmy(missing)}", "days": []}, []
    points = []
    for d, close in zip(series.days, series.values):
        if d < since or d > today:
            continue
        qty, average = book.at(d).get(symbol, (0, Decimal(0)))
        cost = book.adjusted_cost(symbol, d)
        if qty <= 0 or not cost:
            continue
        real = qty * average
        points.append((d, (close / cost - 1) * real, real))
    return {**row, **_summary(points), "days": [{"on": d.isoformat(), "gain": _d(g)} for d, g, _ in points]}, points


def giveback(events, *, closes: dict, today: date) -> dict:
    """closes: {symbol: [(day, close in thousand đồng)]}. Rows for the tickers held today, and the whole portfolio, counted only on days
    every holding that had started by then has a close."""
    series = {s: _Series(p, today, 1000) for s, p in closes.items()}
    book = _Book(events, series)
    held = sorted(s for s, (qty, _) in book.at(today).items() if qty > 0)
    rows, by = [], {}
    for symbol in held:
        row, points = _holding(symbol, book, series.get(symbol) or _Series([], today, 1000), today)
        rows.append(row)
        by[symbol] = (date.fromisoformat(row["since"]), {d: (g, c) for d, g, c in points}, row["reason"])
    missing = [s for s, (_, _, reason) in by.items() if reason]
    total, skipped = [], 0
    if not missing:
        for d in sorted({d for _, points, _ in by.values() for d in points}):
            started = [points for since, points, _ in by.values() if since <= d]
            if any(d not in points for points in started):
                skipped += 1
                continue
            total.append((d, sum(points[d][0] for points in started), sum(points[d][1] for points in started)))
    portfolio = {**_summary(total), "skipped": skipped, "missing": missing,
                 "days": [{"on": d.isoformat(), "gain": _d(g), "value": _d(c + g)} for d, g, c in total]}
    return {"rows": rows, "portfolio": portfolio}


def giveback_alerts(rows: list[dict], *, min_gain: Decimal | None, share: Decimal | None, alerted: set[str]) -> tuple[list[dict], set[str]]:
    """A holding whose peak gain reached min_gain of its cost and that has given back at least share of it is reminded once per holding
    period ("SYMBOL@since"); it re-arms when the share falls back below. Without both thresholds nothing is reminded."""
    if min_gain is None or share is None:
        return [], set()
    alerts, now = [], set()
    for r in rows:
        if not r.get("peak") or r["peak"].get("ratio") is None or r.get("share") is None:
            continue
        key = f"{r['symbol']}@{r['since']}"
        if Decimal(r["peak"]["ratio"]) >= min_gain and Decimal(r["share"]) >= share:
            if key not in alerted:
                alerts.append(r)
            now.add(key)
    return alerts, now


def _runs(days: list[dict], basis: str, amount: Decimal) -> list[tuple[int, int]]:
    out, start = [], None
    for i, d in enumerate(days):
        if Decimal(d[basis]) >= amount:
            start = i if start is None else start
        elif start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(days) - 1))
    return out


def goal_status(goal: dict, days: list[dict]) -> dict:
    """days: the portfolio's [{on, gain, value}]. Whether the goal is covered on the last day and since when; when it is not, the last
    stretch it was covered and by how much at most. Stretches before the goal was set are marked."""
    if not days:
        return {"enough": None, "short": None, "since": None, "days": None, "before_goal": None, "last": None, "last_before_goal": None}
    basis, amount, created = goal["basis"], Decimal(goal["amount"]), goal["created_on"]
    runs, last = _runs(days, basis, amount), days[-1]
    enough = Decimal(last[basis]) >= amount
    out = {"enough": enough, "short": None if enough else _d(amount - Decimal(last[basis])), "since": None, "days": None, "before_goal": None,
           "last": None, "last_before_goal": None}
    if enough:
        since = days[runs[-1][0]]["on"]
        out.update(since=since, days=(date.fromisoformat(last["on"]) - date.fromisoformat(since)).days, before_goal=since < created)
    elif runs:
        a, b = runs[-1]
        top = max(Decimal(days[k][basis]) for k in range(a, b + 1))
        out.update(last={"from": days[a]["on"], "to": days[b]["on"], "excess": _d(top - amount)}, last_before_goal=days[b]["on"] < created)
    return out


def goal_alerts(pairs: list[tuple[dict, dict]], *, states: dict[str, str]) -> tuple[list[dict], dict[str, str]]:
    """pairs: (goal, status). Reminds once when an open goal becomes covered and once when a covered goal falls short again; the first
    time a goal is seen short says nothing. A goal without figures keeps its last known state; a closed goal is forgotten."""
    alerts, now = [], {}
    for goal, status in pairs:
        if goal.get("closed"):
            continue
        before = states.get(goal["id"])
        if status.get("enough") is None:
            if before is not None:
                now[goal["id"]] = before
            continue
        state = "enough" if status["enough"] else "short"
        if state == "enough" and before != "enough":
            alerts.append({"kind": "enough", "goal": goal, "status": status})
        elif state == "short" and before == "enough":
            alerts.append({"kind": "short_again", "goal": goal, "status": status})
        now[goal["id"]] = state
    return alerts, now
