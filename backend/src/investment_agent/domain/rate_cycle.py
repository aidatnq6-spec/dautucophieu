"""Mốc chu kỳ lãi suất: whether rates have risen, fallen or held over about six months, the step VWA's cycle logic starts from
(GDP and inflation → rates → which asset classes usually lead). Vietnam's own rates once six months are stored; until then the US
rates are shown as a labelled reference. Descriptive only: no recommendation."""

from datetime import date, timedelta
from decimal import Decimal

WINDOW = timedelta(days=182)
BAND = Decimal("0.25")  # percentage points: smaller moves count as flat
VIETNAM = ("deposit_12m", "vn10y")
US = ("fed_effr", "us10y")


def six_month_direction(points: list[tuple[date, str]], *, today: date) -> dict | None:
    """Latest value against the last value on or before six months before today; None when less than six months are stored."""
    if not points:
        return None
    earlier = [p for p in points if p[0] <= today - WINDOW]
    if not earlier:
        return None
    then, latest = earlier[-1], points[-1]
    change = Decimal(latest[1]) - Decimal(then[1])
    direction = "up" if change > BAND else "down" if change < -BAND else "flat"
    return {"direction": direction, "change": str(change.quantize(Decimal("0.01"))), "from": then[0].isoformat(), "latest": latest[1]}


def _phase(directions: list[str]) -> str:
    moves = set(directions) - {"flat"}
    return moves.pop() if len(moves) == 1 else "flat"


def rate_cycle(series: dict[str, list[tuple[date, str]]], *, today: date) -> dict:
    def read(ids):
        return [{"id": i, **d} for i in ids if (d := six_month_direction(series.get(i, []), today=today))]
    vietnam = read(VIETNAM)
    firsts = [series[i][0][0] for i in VIETNAM if series.get(i)]
    since = min(firsts) if firsts else None
    out = {"vietnam_since": since.isoformat() if since else None, "vietnam_ready_on": (since + WINDOW).isoformat() if since else None}
    if vietnam:
        return {**out, "basis": "vietnam", "phase": _phase([s["direction"] for s in vietnam]), "series": vietnam}
    us = read(US)
    if us:
        return {**out, "basis": "us_reference", "phase": _phase([s["direction"] for s in us]), "series": us}
    return {**out, "basis": None, "phase": None, "series": []}
