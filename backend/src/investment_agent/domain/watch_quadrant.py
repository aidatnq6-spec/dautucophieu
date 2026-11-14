"""Bong bóng góc phần tư on Theo dõi: each watched ticker placed by two measured things, never by a recommendation.

- across: where today's P/B sits in the ticker's own monthly P/B history (cheaper_months: the share of earlier months with a lower
  P/B; 0 = cheapest so far), from MIN_MONTHS months;
- up: parent net profit of the last four published quarters against the four before them (needs eight quarters, and a profit
  in the earlier four to grow from);
- size: the market value held, for the tickers the owner holds.

The four zones only describe ("rẻ so với chính nó và lợi nhuận đang tăng"…). A ticker short of either measure is listed with why.
"""

from decimal import ROUND_HALF_UP, Decimal

MIN_MONTHS = 24


def _s(v: Decimal) -> str:
    return format(v.normalize(), "f") if v != 0 else "0"


def _growth(quarters: dict[str, dict]) -> tuple[Decimal | None, str | None, str | None]:
    known = [(q, Decimal(r["npat_parent"])) for q, r in sorted(quarters.items()) if r.get("npat_parent") is not None]
    if len(known) < 8:
        return None, None, "chưa đủ 8 quý lợi nhuận"
    recent, before = sum(v for _, v in known[-4:]), sum(v for _, v in known[-8:-4])
    if before <= 0:
        return None, None, "4 quý trước lỗ: không tính được tăng trưởng"
    return ((recent - before) / before).quantize(Decimal("0.0001"), ROUND_HALF_UP), known[-1][0], None


def quadrant(tickers: dict[str, dict], *, held: dict[str, Decimal]) -> dict:
    """tickers: {symbol: {pb: [(month, value or None)] oldest first, quarters: {period: {npat_parent}}}}; held: market value by symbol."""
    points, missing = [], {}
    for symbol, t in sorted(tickers.items()):
        series = [Decimal(v) for _, v in t.get("pb") or [] if v is not None]
        growth, quarter, why = _growth(t.get("quarters") or {})
        if len(series) < MIN_MONTHS:
            missing[symbol] = f"chưa đủ {MIN_MONTHS} tháng P/B"
            continue
        if growth is None:
            missing[symbol] = why
            continue
        now, before = series[-1], series[:-1]
        cheaper = (Decimal(sum(1 for v in before if v < now)) / len(before)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        zone = f"{'cheap' if cheaper < Decimal('0.5') else 'dear'}_{'growing' if growth > 0 else 'shrinking'}"
        points.append({"symbol": symbol, "pb": _s(now.quantize(Decimal("0.01"), ROUND_HALF_UP)), "cheaper_months": _s(cheaper), "months": len(series),
                       "growth": _s(growth), "quarter": quarter, "held": _s(held[symbol]) if symbol in held else None, "zone": zone})
    return {"points": points, "missing": missing}
