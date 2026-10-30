"""Daily P/E and P/B of VNINDEX and VN30 from VNDirect's public ratios API (the source Vnstock reads for these, outside
the Community tier). robots.txt of api-finfo.vndirect.com.vn allows all user agents (use=reference, checked 31/10/2026).

The first sync takes the whole history (from 15/12/2017); later ones the last 14 days before the latest stored point,
so restated values are picked up. Rows for another index or ratio, and non-positive values, are dropped, never repaired.
"""

import json
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Callable

from .leading import _get_with_retry
from .series import SeriesStore

INDICES = ("VNINDEX", "VN30")
RATIOS = {"pe": "PRICE_TO_EARNINGS", "pb": "PRICE_TO_BOOK"}
URL = "https://api-finfo.vndirect.com.vn/v4/ratios?q=ratioCode:{ratio}~code:{index}~reportDate:gte:{start}&sort=reportDate:asc&size=5000"
FIRST_START = date(2017, 1, 1)
OVERLAP_DAYS = 14


def series_key(index: str, ratio: str) -> str:
    return f"{index}-{ratio}-1d"


def parse_ratios(text: str, *, index: str, ratio_code: str) -> list[tuple[datetime, str]]:
    out = []
    for row in json.loads(text).get("data") or []:
        if row.get("code") != index or row.get("ratioCode") != ratio_code:
            continue
        try:
            value = Decimal(str(row["value"]))
            day = date.fromisoformat(row["reportDate"])
        except (InvalidOperation, KeyError, TypeError, ValueError):
            continue
        if value.is_finite() and value > 0:
            out.append((datetime.combine(day, datetime.min.time()), format(value.normalize(), "f")))
    return out


def fetch_index_valuation(store: SeriesStore, *, get: Callable[[str], str], today: date,
                          sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """Update each index/ratio series; a failing one is reported and the others still update."""
    results = {}
    for index in INDICES:
        for ratio, code in RATIOS.items():
            key = series_key(index, ratio)
            stored = store.read(key)
            start = stored[-1][0].date() - timedelta(days=OVERLAP_DAYS) if stored else FIRST_START
            try:
                points = parse_ratios(_get_with_retry(get, URL.format(ratio=code, index=index, start=start.isoformat()), sleep),
                                      index=index, ratio_code=code)
                if not points:
                    results[f"{index}-{ratio}"] = "error:no_observations"
                    continue
                store.upsert(key, [p for p in points if p[0].date() <= today])
                results[f"{index}-{ratio}"] = "ok"
            except Exception as exc:
                results[f"{index}-{ratio}"] = f"error:{type(exc).__name__}"
    return results
