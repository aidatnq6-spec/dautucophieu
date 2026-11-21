"""Dòng tiền & kỹ thuật (owner, 21/11/2026): one row per watched ticker from stored public data.

- Volume against the average of the 20 sessions before, and where the close sits in the session's high-low range (daily bars).
- Foreign net of the last session (session snapshots) and how many sessions in a row it kept the same side.
- 52-week high and low, MA20 and MA50, all on closing prices (the long history has closes only), and the crossings of the last session.

A figure that needs more history than is stored is None and named in "missing"; nothing is estimated. Describes; never recommends."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

FLAGS = ("volume_spike", "new_high", "new_low", "cross_up_ma20", "cross_up_ma50", "cross_down_ma20", "cross_down_ma50", "foreign_buy_5",
         "foreign_sell_5")
SPIKE = Decimal(2)       # volume at least twice the 20-session average
RUN = 5                  # foreign net on the same side at least this many sessions in a row
YEAR = timedelta(days=365)

Closes = list[tuple[date, Decimal]]          # thousand đồng, oldest first
Bars = list[tuple[date, Decimal, Decimal, Decimal, int]]  # (day, high, low, close in đồng, volume), oldest first


def _q(value: Decimal, places: str) -> str:
    return format(value.quantize(Decimal(places), ROUND_HALF_UP), "f")


def _dong(value: Decimal) -> str:
    return _q(value * 1000, "1")


def _ma(values: list[Decimal], n: int) -> Decimal:
    return sum(values[-n:], Decimal(0)) / n


def stock_row(symbol: str, *, closes: Closes, bars: Bars, foreign: list[tuple[date, Decimal]], held: bool) -> dict:
    row = {"symbol": symbol, "held": held, "date": None, "close": None, "pct": None, "volume": None, "volume_ratio": None,
           "range_position": None, "foreign_net_bn": None, "foreign_run": None, "high_52w": None, "low_52w": None, "ma20": None, "ma50": None,
           "flags": [], "missing": []}
    if len(closes) < 2:
        row["missing"] = ["closes"]
        return row
    last_day, last = closes[-1]
    values = [v for _, v in closes]
    row.update(date=last_day.isoformat(), close=_dong(last), pct=_q(last / values[-2] - 1, "0.0001") if values[-2] else None)
    flags, missing = row["flags"], row["missing"]

    if len(bars) >= 21 and bars[-1][0] == last_day:
        _, high, low, close, volume = bars[-1]
        average = Decimal(sum(b[4] for b in bars[-21:-1])) / 20
        row["volume"] = volume
        if average > 0:
            ratio = Decimal(volume) / average
            row["volume_ratio"] = _q(ratio, "0.01")
            if ratio >= SPIKE:
                flags.append("volume_spike")
        if high > low:
            row["range_position"] = _q((close - low) / (high - low), "0.01")
    else:
        missing.append("volume_20")

    if foreign and foreign[-1][0] == last_day:
        net = foreign[-1][1]
        row["foreign_net_bn"] = format(net.normalize(), "f") if net else "0"
        run = 0
        for _, v in reversed(foreign):
            if v == 0 or (run and (v > 0) != (run > 0)):
                break
            run += 1 if v > 0 else -1
        row["foreign_run"] = run
        if run >= RUN:
            flags.append("foreign_buy_5")
        elif run <= -RUN:
            flags.append("foreign_sell_5")

    if closes[0][0] <= last_day - YEAR:
        window = [v for d, v in closes[:-1] if d > last_day - YEAR]
        high52, low52 = max(window), min(window)
        row.update(high_52w=_dong(high52), low_52w=_dong(low52))
        if last > high52:
            flags.append("new_high")
        if last < low52:
            flags.append("new_low")
    else:
        missing.append("52w")

    for n in (20, 50):
        if len(values) < n + 1:
            missing.append(f"ma{n}")
            continue
        now, before = _ma(values, n), _ma(values[:-1], n)
        row[f"ma{n}"] = _dong(now)
        if values[-2] <= before and last > now:
            flags.append(f"cross_up_ma{n}")
        elif values[-2] >= before and last < now:
            flags.append(f"cross_down_ma{n}")
    return row


def flag_counts(rows: list[dict]) -> dict[str, int]:
    return {f: sum(1 for r in rows if f in r["flags"]) for f in FLAGS}
