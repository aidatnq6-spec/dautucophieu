"""Hiệu suất theo kỳ for Chuỗi giá trị (owner, 21/11/2026): how each chain's listed members moved over a week, a month, three months,
a year and since the year began, on stored closes.

A member's change over a period is its last close against its last close on or before the period's start (for the year to date, the
last close of the previous year). A chain's change is the equal-weighted average over the members that have that figure, with their
count: market values are not stored for every member, so no weighting is guessed. A member with no close in the last 10 days is left
out and named. Describes; never recommends."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from statistics import median

PERIODS = {"w1": 7, "m1": 30, "m3": 91, "y1": 365}
STALE = timedelta(days=10)
YEAR = timedelta(days=365)

Closes = list[tuple[date, Decimal]]


def _q(value: Decimal, places: str = "0.0001") -> str:
    return format(value.quantize(Decimal(places), ROUND_HALF_UP), "f")


def period_change(closes: Closes, *, days: int | None = None, ytd: bool = False) -> Decimal | None:
    if len(closes) < 2:
        return None
    last_day, last = closes[-1]
    start = date(last_day.year - 1, 12, 31) if ytd else last_day - timedelta(days=days)
    base = [v for d, v in closes if d <= start]
    if not base or not base[-1]:
        return None
    return last / base[-1] - 1


def _position(closes: Closes) -> Decimal | None:
    last_day, last = closes[-1]
    if closes[0][0] > last_day - YEAR:
        return None
    window = [v for d, v in closes if d > last_day - YEAR]
    high, low = max(window), min(window)
    return (last - low) / (high - low) if high > low else None


def chain_returns(chains: list[dict], closes: dict[str, Closes], *, today: date) -> list[dict]:
    out = []
    for chain in chains:
        symbols = list(dict.fromkeys(chain["symbols"]))
        live, no_data, stale = {}, [], []
        for s in symbols:
            c = closes.get(s) or []
            if len(c) < 2:
                no_data.append(s)
            elif today - c[-1][0] > STALE:
                stale.append(s)
            else:
                live[s] = c
        periods = {}
        for key, days in (*PERIODS.items(), ("ytd", None)):
            changes = [ch for c in live.values() if (ch := period_change(c, days=days, ytd=key == "ytd")) is not None]
            periods[key] = {"change": _q(sum(changes, Decimal(0)) / len(changes)) if changes else None, "n": len(changes)}
        moves = [c[-1][1] - c[-2][1] for c in live.values()]
        month = {s: ch for s, c in live.items() if (ch := period_change(c, days=PERIODS["m1"])) is not None}
        positions = [p for c in live.values() if (p := _position(c)) is not None]
        leader = max(month, key=month.get) if month else None
        out.append({"id": chain["id"], "name": chain["name"], "members": len(symbols), "priced": len(live), "no_data": no_data, "stale": stale,
                    "periods": periods, "breadth": {"up": sum(m > 0 for m in moves), "down": sum(m < 0 for m in moves), "flat": sum(m == 0 for m in moves)},
                    "position_52w": _q(Decimal(median(positions)), "0.01") if positions else None,
                    "leader": {"symbol": leader, "m1": _q(month[leader])} if leader else None})
    return out
