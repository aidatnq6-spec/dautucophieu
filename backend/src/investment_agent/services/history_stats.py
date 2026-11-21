"""Thống kê lịch sử: reads the stored public series (VN-Index closes, VN-Index P/E, oil, the broad dollar, the US 10-year yield) and
hands them to domain.history_stats. Results are kept in memory for the day: about two seconds to work out, the series change daily."""

from __future__ import annotations

import time
from datetime import date
from decimal import Decimal
from pathlib import Path

from investment_agent.domain.history_stats import light_groups, pe_groups
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore

HORIZONS = (20, 60, 120, 250)
LIGHTS = ("oil", "usd", "us10y", "pe")
_CACHE: dict = {}
TTL_SECONDS = 3600


def _series(store: SeriesStore, key: str) -> list[tuple[date, Decimal]]:
    return [(t.date(), Decimal(str(v))) for t, v in store.read(key) if v]


def _macro(data_dir: Path, key: str) -> list[tuple[date, Decimal]]:
    return [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in MacroStore(data_dir).read(key)]


def history_stats(data_dir: Path, *, h: int, today: date) -> dict:
    key = (str(data_dir), h, today)
    hit = _CACHE.get(key)
    if hit and time.monotonic() - hit[0] < TTL_SECONDS:
        return hit[1]
    data_dir = Path(data_dir)
    closes = _series(SeriesStore(data_dir / "trend-sources"), "VNINDEX-1d")
    pe = _series(SeriesStore(data_dir / "index-valuation"), "VNINDEX-pe-1d")
    series = {"factor_oil": _macro(data_dir, "factor_oil"), "factor_usd": _macro(data_dir, "factor_usd"), "us10y": _macro(data_dir, "us10y"),
              "vnindex_pe": pe}
    out = {"h": h, "horizons": list(HORIZONS), "closes_from": closes[0][0].isoformat() if closes else None,
           "pe": pe_groups(pe, closes, h=h), "lights": [light_groups(k, series, closes, h=h) for k in LIGHTS]}
    _CACHE.clear() if len(_CACHE) > 16 else None
    _CACHE[key] = (time.monotonic(), out)
    return out
