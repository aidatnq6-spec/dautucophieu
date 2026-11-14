"""Lưới biểu đồ nhỏ: each held ticker's last twelve months of adjusted daily closes, one point a week (the week's last close),
rebased to 100 on the first week, with VN-Index rebased the same way, so who led and who lagged the market reads at a glance. A
ticker without twelve months of closes is listed, not drawn on a shorter span."""

from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

DAYS = 365


def _weekly(points: list[tuple[datetime, float]], start: date, today: date) -> dict[date, Decimal]:
    """The last close of each ISO week from start, keyed by that close's day."""
    weeks: dict[tuple[int, int], tuple[date, Decimal]] = {}
    for t, v in points:
        d = t.date()
        if start <= d <= today:
            weeks[d.isocalendar()[:2]] = (d, Decimal(str(v)))
    return dict(sorted(weeks.values()))


def _r(v: Decimal) -> str:
    q = v.quantize(Decimal("0.1"), ROUND_HALF_UP)
    return format(q.normalize(), "f") if q != 0 else "0"


def small_multiples(series: dict[str, list[tuple[datetime, float]]], *, index: list[tuple[datetime, float]], today: date) -> dict:
    start = today - timedelta(days=DAYS)
    idx = _weekly(index, start, today)
    charts, short = [], {}
    for symbol, points in sorted(series.items()):
        if not points or points[0][0].date() > start + timedelta(days=7):
            short[symbol] = "chưa đủ 12 tháng giá"
            continue
        weekly = _weekly(points, start, today)
        days = [d for d in weekly if d in idx]
        if len(days) < 2:
            short[symbol] = "chưa đủ 12 tháng giá"
            continue
        b, bi = weekly[days[0]], idx[days[0]]
        pts = [{"date": d.isoformat(), "value": _r(weekly[d] / b * 100), "index": _r(idx[d] / bi * 100)} for d in days]
        charts.append({"symbol": symbol, "points": pts, "change": pts[-1]["value"], "index_change": pts[-1]["index"],
                       "ahead": Decimal(pts[-1]["value"]) > Decimal(pts[-1]["index"])})
    charts.sort(key=lambda c: -Decimal(c["change"]))
    return {"charts": charts, "short": short}
