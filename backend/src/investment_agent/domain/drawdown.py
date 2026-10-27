"""Kế hoạch sụt giảm: how deep a price has fallen from a peak (in all stored history, and right now), and a reminder when a held
ticker falls past the owner's own threshold below their cost. It reports; it never says to sell."""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

_Q4 = Decimal("0.0001")


def _ratio(value: float) -> str:
    return str(Decimal(str(value)).quantize(_Q4, ROUND_HALF_UP))


def _priced(points: list[tuple[datetime, float]]) -> list[tuple[datetime, float]]:
    """Only real prices: the source sometimes returns 0 for very old sessions (NT2), which would divide by zero."""
    return [p for p in points if p[1] > 0]


def max_drawdown(points: list[tuple[datetime, float]]) -> dict | None:
    """Deepest close-to-close fall from a running peak: depth (≤ 0), peak and trough dates, and the first date back at the peak."""
    points = _priced(points)
    if not points:
        return None
    peak_i, best = 0, (0.0, 0, 0)
    for i, (_, close) in enumerate(points):
        if close > points[peak_i][1]:
            peak_i = i
        depth = close / points[peak_i][1] - 1
        if depth < best[0]:
            best = (depth, peak_i, i)
    depth, p, t = best
    recovered = next((d for d, c in points[t + 1:] if c >= points[p][1]), None) if depth < 0 else None
    return {"depth": _ratio(depth), "peak": points[p][0].date().isoformat(), "trough": points[t][0].date().isoformat(),
            "recovered": recovered.date().isoformat() if recovered else None}


def current_drawdown(points: list[tuple[datetime, float]]) -> dict | None:
    points = _priced(points)
    if not points:
        return None
    peak = max(points, key=lambda p: p[1])
    return {"depth": _ratio(points[-1][1] / peak[1] - 1), "peak": peak[0].date().isoformat()}


def threshold_alerts(holdings: dict[str, dict], *, threshold: str, alerted: set[str]) -> tuple[list[dict], set[str]]:
    """holdings: {symbol: {price, cost}} in đồng. A ticker at or below −threshold from its average cost alerts once; it re-arms
    when it climbs back above. Returns (new alerts, symbols currently alerted)."""
    limit, alerts, now = -Decimal(threshold), [], set(alerted)
    for symbol, h in sorted(holdings.items()):
        if h.get("price") is None or not h.get("cost") or Decimal(h["cost"]) <= 0:
            continue
        change = Decimal(h["price"]) / Decimal(h["cost"]) - 1
        if change <= limit and symbol not in now:
            alerts.append({"symbol": symbol, "change": str(change.quantize(_Q4, ROUND_HALF_UP)), "price": h["price"], "cost": h["cost"]})
            now.add(symbol)
        elif change > limit:
            now.discard(symbol)
    return alerts, now
