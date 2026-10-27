"""Kiểm tra trước khi mua: concentration after the buy, the asset pyramid after it, and whether the ticker has run up lately (FOMO).

It asks the owner to look again; it never blocks a trade or says whether to buy."""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

LOOKBACK = timedelta(days=92)  # about three months


def three_month_change(points: list[tuple[datetime, float]]) -> dict | None:
    """Last close against the last close on or before three months earlier; None when less than three months are stored."""
    if not points:
        return None
    cutoff = points[-1][0] - LOOKBACK
    earlier = [p for p in points if p[0] <= cutoff]
    if not earlier:
        return None
    then = earlier[-1]
    change = Decimal(str(points[-1][1])) / Decimal(str(then[1])) - 1
    return {"change": str(change.quantize(Decimal("0.0001"), ROUND_HALF_UP)), "from": then[0].date().isoformat()}


def buy_flags(*, ticker: dict | None, sector: dict | None, limit: str, pyramid_warnings: list[dict], stocks_over: bool,
              momentum: dict | None, fomo: str) -> list[dict]:
    flags = []
    if ticker and ticker.get("over"):
        flags.append({"kind": "ticker", "symbol": ticker["symbol"], "weight": ticker["weight"], "limit": limit})
    if sector and sector.get("over"):
        flags.append({"kind": "sector", "sector": sector["sector"], "weight": sector["weight"], "limit": limit})
    if stocks_over:
        flags.append({"kind": "stocks_layer"})
    for w in pyramid_warnings:
        flags.append({"kind": "bottom_up", "short": w["short"], "over": w["over"]})
    if momentum and Decimal(momentum["change"]) >= Decimal(fomo):
        flags.append({"kind": "fomo", "change": momentum["change"], "from": momentum["from"], "threshold": fomo})
    return flags
