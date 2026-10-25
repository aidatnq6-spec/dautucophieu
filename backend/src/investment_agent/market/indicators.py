"""MACD and RSI as TradingView computes them by default, and bar resampling for the trend board.

EMA uses alpha 2/(n+1) seeded with the simple average of the first n values (Pine ta.ema); RSI
smooths gains and losses with Wilder's average seeded the same way (Pine ta.rsi). Indicators are
ratios of prices, not money, so floats are used here. Points are (datetime, close) sorted ascending.
"""

from datetime import timezone
from decimal import ROUND_HALF_UP, Decimal

MIN_MACD_BARS, MIN_RSI_BARS = 35, 15


def ema(values: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if len(values) < n:
        return out
    prev = sum(values[:n]) / n
    out[n - 1] = prev
    alpha = 2 / (n + 1)
    for i in range(n, len(values)):
        prev = alpha * values[i] + (1 - alpha) * prev
        out[i] = prev
    return out


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[list[float | None], list[float | None]]:
    line = [a - b if a is not None and b is not None else None for a, b in zip(ema(closes, fast), ema(closes, slow))]
    start = next((i for i, v in enumerate(line) if v is not None), len(line))
    return line, [None] * start + ema(line[start:], signal)


def rsi(closes: list[float], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) < n + 1:
        return out
    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]

    def value(g, l):
        return 100.0 if l == 0 else 0.0 if g == 0 else 100 - 100 / (1 + g / l)
    avg_g, avg_l = sum(gains[:n]) / n, sum(losses[:n]) / n
    out[n] = value(avg_g, avg_l)
    for i in range(n + 1, len(closes)):
        avg_g = (avg_g * (n - 1) + gains[i - 1]) / n
        avg_l = (avg_l * (n - 1) + losses[i - 1]) / n
        out[i] = value(avg_g, avg_l)
    return out


def macd_state(closes: list[float]) -> str | None:
    """"up"/"down": MACD above/below its signal on the last bar; ">0"/"<0": the MACD line's sign."""
    if len(closes) < MIN_MACD_BARS:
        return None
    line, signal = macd(closes)
    return f"{'up' if line[-1] > signal[-1] else 'down'},{'>0' if line[-1] > 0 else '<0'}"


def rsi_value(closes: list[float]) -> int | None:
    if len(closes) < MIN_RSI_BARS:
        return None
    return int(Decimal(str(rsi(closes)[-1])).quantize(Decimal(1), ROUND_HALF_UP))


def _last_per(points, key) -> list[float]:
    out, last = [], object()
    for t, v in points:
        k = key(t)
        if out and k == last:
            out[-1] = v
        else:
            out.append(v)
            last = k
    return out


def weekly(points) -> list[float]:
    return _last_per(points, lambda t: t.isocalendar()[:2])


def monthly(points) -> list[float]:
    return _last_per(points, lambda t: (t.year, t.month))


def four_hourly(points) -> list[float]:
    """Four-hour bars anchored at 00:00 UTC (07:00 in Vietnam), as TradingView draws them."""
    def key(t):
        u = t.astimezone(timezone.utc)
        return u.date(), u.hour // 4
    return _last_per(points, key)
