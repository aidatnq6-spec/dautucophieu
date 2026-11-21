"""Chứng khoán Mỹ (owner, 21/11/2026): S&P 500, Nasdaq Composite and Dow Jones from FRED's daily series (the CSV the app already reads
for other series; robots.txt allows it). Read with macro-sync and kept in the macro store. Unlike the Asian indices (VNDirect gives no
session date), each figure carries its own session date. A holiday ("." in FRED) is skipped, never filled."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable

from investment_agent.market.leading import FRED_CSV, MacroStore, _get_with_retry, error_name, parse_fred_csv

INDICES = (("us_sp500", "SP500", "S&P 500"), ("us_nasdaq", "NASDAQCOM", "Nasdaq Composite"), ("us_dow", "DJIA", "Dow Jones"))
KEEP = 400          # sessions kept: a year and a half
MAX_AGE_DAYS = 7    # a figure older than this no longer stands for the latest US session (macro-sync's "late" rule too)


def fetch_us_indices(store: MacroStore, *, get: Callable[[str], str], sleep) -> dict[str, str]:
    results = {}
    for key, series, _ in INDICES:
        url = FRED_CSV.format(series=series)
        try:
            points = parse_fred_csv(_get_with_retry(get, url, sleep))
            if not points:
                raise ValueError("no_observations")
            store.upsert(key, points[-KEEP:], entry="auto", source_url=url)
            results[key] = "ok"
        except Exception as exc:
            results[key] = f"error:{error_name(exc)}"
    return results


def _pct(now: Decimal, before: Decimal | None) -> str | None:
    return str((now / before - 1).quantize(Decimal("0.0001"), ROUND_HALF_UP)) if before else None


def us_indices(store: MacroStore, *, today: date) -> dict:
    rows = []
    for key, series, name in INDICES:
        obs = [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(key)]
        if not obs:
            continue
        day, close = obs[-1]
        month = [v for d, v in obs if d <= day - timedelta(days=30)]
        rows.append({"id": key, "series": series, "name": name, "close": format(close.normalize(), "f"), "date": day.isoformat(),
                     "day_pct": _pct(close, obs[-2][1]) if len(obs) >= 2 else None, "m1_pct": _pct(close, month[-1]) if month else None,
                     "stale": (today - day).days > MAX_AGE_DAYS})
    return {"rows": rows, "source": "FRED"}
