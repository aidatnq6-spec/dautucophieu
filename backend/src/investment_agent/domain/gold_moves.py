"""Vàng: sụt từ đỉnh và độ truyền giá (owner's choice, 20/11/2026). Public prices only; nothing is estimated or filled in.

- drawdown: the latest figure against the highest since the first stored one. The history is only what is kept, so the page says from when.
- pass_through: how far SJC moved against the world price in đồng over about 30 days, both from their own stored days; no figure is
  carried to a day it was not read, except the exchange rate, taken from the latest day up to 7 days before (weekends, holidays)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

CHI_PER_OZ = Decimal("31.1034768") / Decimal("3.75")  # grams an ounce over grams a chỉ, as the SJC gap
WINDOW_DAYS = 30
FX_MAX_GAP_DAYS = 7


def _ratio(new: Decimal, old: Decimal) -> str:
    return str((new / old - 1).quantize(Decimal("0.0001"), ROUND_HALF_UP))


def drawdown(points: list[tuple[date, Decimal]], *, today: date, max_age_days: int) -> dict:
    if not points:
        return {"since": None, "peak": None, "peak_date": None, "latest": None, "latest_date": None, "change": None, "stale": False,
                "missing": "no_data"}
    points = sorted(points)
    peak_date, peak = max(points, key=lambda p: (p[1], p[0]))  # the latest day of an equal high
    latest_date, latest = points[-1]
    return {"since": points[0][0].isoformat(), "peak": str(peak), "peak_date": peak_date.isoformat(), "latest": str(latest),
            "latest_date": latest_date.isoformat(), "change": _ratio(latest, peak), "stale": (today - latest_date).days > max_age_days,
            "missing": None}


def _world_in_dong(xau: list[tuple[date, Decimal]], fx: list[tuple[date, Decimal]]) -> dict[date, Decimal]:
    fx = sorted(fx)
    out = {}
    for day, usd in xau:
        rate_day, rate = next(((d, r) for d, r in reversed(fx) if d <= day), (None, None))
        if rate is not None and (day - rate_day).days <= FX_MAX_GAP_DAYS:
            out[day] = (usd * rate / CHI_PER_OZ).quantize(Decimal("1"), ROUND_HALF_UP)
    return out


def pass_through(sjc: list[tuple[date, Decimal]], xau: list[tuple[date, Decimal]], fx: list[tuple[date, Decimal]], *, today: date) -> dict:
    empty = {"days": None, "from": None, "to": None, "sjc_from": None, "sjc_to": None, "world_from": None, "world_to": None,
             "sjc_change": None, "world_change": None}
    world, local = _world_in_dong(xau, fx), dict(sjc)
    common = sorted(d for d in local if d in world)
    if not common:
        return {"missing": "no_data", "since": None, "ready_on": None, **empty}
    end = common[-1]
    start = next((d for d in reversed(common) if d <= end - timedelta(days=WINDOW_DAYS)), None)
    if start is None:
        return {"missing": "not_enough_history", "since": common[0].isoformat(),
                "ready_on": (common[0] + timedelta(days=WINDOW_DAYS)).isoformat(), **empty}
    return {"missing": None, "since": common[0].isoformat(), "ready_on": None, "days": (end - start).days, "from": start.isoformat(),
            "to": end.isoformat(), "sjc_from": str(local[start]), "sjc_to": str(local[end]), "world_from": str(world[start]),
            "world_to": str(world[end]), "sjc_change": _ratio(local[end], local[start]), "world_change": _ratio(world[end], world[start])}


# Nhắc "đừng hành động theo giá" (owner's choice, 20/11/2026): a move of 10% or more either way over about 30 days, shown where gold is
# recorded. Each kind's own buying price once it has 30 days; before that the world price (PAXG-USD), said so on the page.
STRONG_MOVE = Decimal("0.10")
WINDOW_SLACK_DAYS = 7  # the earlier price may be up to a week older than 30 days (days the price was not read); never more


def recent_move(points: list[tuple[date, Decimal]], *, today: date, max_age_days: int) -> dict | None:
    """The latest price against the latest one at least 30 days before it; None when the latest is old or there is no such price."""
    if not points:
        return None
    points = sorted(points)
    end, last = points[-1]
    if (today - end).days > max_age_days:
        return None
    start = next(((d, v) for d, v in reversed(points) if d <= end - timedelta(days=WINDOW_DAYS)), None)
    if start is None or (end - start[0]).days > WINDOW_DAYS + WINDOW_SLACK_DAYS:
        return None
    change = last / start[1] - 1
    return {"from": start[0].isoformat(), "to": end.isoformat(), "days": (end - start[0]).days, "change": _ratio(last, start[1]),
            "strong": abs(change) >= STRONG_MOVE}


def price_moves(kinds: dict[str, list[tuple[date, Decimal]]], world: list[tuple[date, Decimal]], *, today: date,
                kind_max_age: int = 3, world_max_age: int = 7) -> dict:
    """{"threshold", "world": move or None, "kinds": {kind: move}}; each move says its basis ("kind" or "world")."""
    w = recent_move(world, today=today, max_age_days=world_max_age)
    w = {"basis": "world", **w} if w else None
    out = {}
    for kind, points in kinds.items():
        own = recent_move(points, today=today, max_age_days=kind_max_age)
        if own or w:
            out[kind] = {"basis": "kind", **own} if own else w
    return {"threshold": str(STRONG_MOVE), "world": w, "kinds": out}
