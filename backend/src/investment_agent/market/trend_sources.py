"""Public close feeds for the trend board's non-Vietnamese rows.

Coinbase Exchange public candles (no account): at most 300 candles per call, newest first, rows
[time, low, high, open, close, volume]. FRED public CSV: one close per day.
"""

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from .leading import ECB_90D, FRED_CSV, parse_ecb_dxy, parse_fred_csv

ECB_FULL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml"  # all reference rates since 1999 (a few MB)

COINBASE = "https://api.exchange.coinbase.com/products/{product}/candles?granularity={g}&start={s}&end={e}"


def coinbase_closes(get, product: str, granularity: int, start: date, end: date) -> list[tuple[datetime, str]]:
    span = timedelta(seconds=granularity * 300)
    t0 = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)
    t_end = datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
    seen: dict[datetime, str] = {}
    while t0 < t_end:
        t1 = min(t0 + span, t_end)
        url = COINBASE.format(product=product, g=granularity, s=t0.isoformat().replace("+00:00", "Z"), e=t1.isoformat().replace("+00:00", "Z"))
        for row in json.loads(get(url)):
            seen[datetime.fromtimestamp(int(row[0]), timezone.utc)] = format(Decimal(str(row[4])).normalize(), "f")
        t0 = t1
    return sorted(seen.items())


def fred_closes(get, series: str, start: date) -> list[tuple[datetime, str]]:
    text = get(FRED_CSV.format(series=series) + f"&cosd={start.isoformat()}")
    return [(datetime(d.year, d.month, d.day), v) for d, v in parse_fred_csv(text)]


def ecb_dxy_closes(get, *, have: int, enough: int = 400) -> list[tuple[datetime, str]]:
    """DXY by ICE's formula from ECB reference rates: the full history until the series is long enough, then the last 90 days."""
    points = parse_ecb_dxy(get(ECB_FULL if have < enough else ECB_90D))
    return [(datetime(d.year, d.month, d.day), v) for d, v in points]
