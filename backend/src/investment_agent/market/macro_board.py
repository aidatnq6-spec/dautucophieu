"""Vĩ mô rows of the Xu hướng price board: DXY, US10Y, VN10Y, gold, WTI oil and Bitcoin, from the series the app already keeps
(trend-sources, intraday, the macro store). Bitcoin and gold (PAXG) are read live from Coinbase's public stats and compared with
24 hours before; the others are the last daily close against the one before, dated. A single close gives no change; a missing
series says so. Charts are close lines, since these feeds have closes only.
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from investment_agent.market.indicators import macd, rsi
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore

VN = timezone(timedelta(hours=7))
STATS = "https://api.exchange.coinbase.com/products/{product}/stats"
# id, label, unit, Coinbase product for a live price, whether an hourly series is kept
MACRO = (("DXY", "DXY", "điểm", None, False), ("US10Y", "US10Y", "%", None, False), ("VN10Y", "VN10Y", "%", None, False),
         ("GOLD", "Vàng", "USD/oz", "PAXG-USD", True), ("USOIL", "Dầu WTI", "USD/thùng", None, False),
         ("BTC", "Bitcoin", "USD", "BTC-USD", True))
IDS = {m[0] for m in MACRO}
# DXY is kept under its own key since it is computed from ECB rates; "DXY-1d" holds FRED's broad dollar index, a different level.
SERIES = {"DXY": "DXY-ecb-1d"}


def _dec(v) -> Decimal | None:
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return d if d.is_finite() else None


def _s(d: Decimal) -> str:
    return "0" if d == 0 else format(d.normalize(), "f")


def _daily(data_dir: Path, symbol: str) -> list[tuple[str, str]]:
    if symbol == "VN10Y":
        return [(o["date"], o["value"]) for o in sorted(MacroStore(data_dir).read("vn10y"), key=lambda o: o["date"])]
    return [(t[:10], v) for t, v in SeriesStore(data_dir / "trend-sources").points(SERIES.get(symbol, f"{symbol}-1d"))]


def _row(symbol, label, unit, price, ref, when, basis, reason=None) -> dict:
    change = price - ref if price is not None and ref is not None else None
    return {"symbol": symbol, "kind": "macro", "label": label, "price": _s(price) if price is not None else None,
            "ref": _s(ref) if ref is not None else None, "change": _s(change) if change is not None else None,
            "change_pct": format((change / ref).quantize(Decimal("0.0001"), ROUND_HALF_UP), "f") if change is not None and ref else None,
            "time": when, "basis": basis, "unit": unit, "reason": reason}


def macro_rows(data_dir: Path, *, get: Callable[[str], str], now: datetime) -> list[dict]:
    rows = []
    for symbol, label, unit, product, _ in MACRO:
        if product:
            try:
                stats = json.loads(get(STATS.format(product=product)))
                last, opened = _dec(stats.get("last")), _dec(stats.get("open"))
                if last is not None and last > 0:
                    rows.append(_row(symbol, label, unit, last, opened if opened and opened > 0 else None, now.isoformat(), "24h"))
                    continue
            except Exception:
                pass  # the daily close below stands in
        points = [(t, _dec(v)) for t, v in _daily(Path(data_dir), symbol) if _dec(v) is not None]
        if not points:
            rows.append(_row(symbol, label, unit, None, None, None, "close", "Chưa có số"))
            continue
        rows.append(_row(symbol, label, unit, points[-1][1], points[-2][1] if len(points) > 1 else None, points[-1][0], "close"))
    return rows


def macro_chart(data_dir: Path, symbol: str, interval: str) -> dict:
    label, unit, hourly = next((m[1], m[2], m[4]) for m in MACRO if m[0] == symbol)
    base = {"symbol": symbol, "interval": interval, "style": "line", "bars": [], "macd": [], "rsi": [], "fetched_at": None, "as_of": None,
            "stale": False, "unit": unit}
    if interval == "1H" and not hourly:
        return {**base, "reason": "Nguồn chỉ có giá ngày"}
    if interval == "1H":
        raw = SeriesStore(Path(data_dir) / "intraday").points(f"{symbol}-1h")
        bars = [{"t": int(datetime.fromisoformat(t).astimezone(VN).replace(tzinfo=timezone.utc).timestamp()), "c": v} for t, v in raw]
    else:
        bars = [{"t": t, "c": v} for t, v in _daily(Path(data_dir), symbol)]
    bars = [b for b in bars if _dec(b["c"]) is not None]
    if not bars:
        return {**base, "reason": "Chưa có số"}
    closes = [float(b["c"]) for b in bars]
    line, signal = macd(closes)
    m = [{"t": b["t"], "macd": round(a, 4), "signal": round(s, 4), "hist": round(a - s, 4)} for b, a, s in zip(bars, line, signal)
         if a is not None and s is not None]
    r = [{"t": b["t"], "v": round(v, 2)} for b, v in zip(bars, rsi(closes)) if v is not None]
    as_of = bars[-1]["t"] if isinstance(bars[-1]["t"], str) else datetime.fromtimestamp(bars[-1]["t"], timezone.utc).strftime("%Y-%m-%d %H:%M")
    return {**base, "bars": bars, "macd": m, "rsi": r, "as_of": as_of, "reason": None, "label": label}
