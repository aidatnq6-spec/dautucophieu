"""Bảng giá và biểu đồ on Xu hướng: prices during the session for the indices and the watchlist, and candles with MACD/RSI for
one ticker, from Vnstock's free tier.

Stocks come from the price board in one call (đồng, shown in thousands like the exchanges' boards). The board does not serve
indices, so VNINDEX and VN30 are read from minute bars: the last bar is the level, the last bar of the previous session the
reference. A ticker not yet traded today has no price; the reference is never shown as a price. Candles are cached in
data/chart/<MÃ>-<khung>.json; the saved copy is shown, dated, when the source fails.
"""

import json
import os
import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from investment_agent.market.indicators import macd, rsi

VN = timezone(timedelta(hours=7))
INDICES = ("VNINDEX", "VN30")
THOUSAND = Decimal(1000)
OPEN, CLOSE = time(9, 0), time(15, 0)
INTERVALS = {"1D": timedelta(days=3650), "1H": timedelta(days=365)}
# How long saved candles stay fresh: the last bar moves during the session.
FRESH = {("1D", True): timedelta(minutes=10), ("1D", False): timedelta(hours=6),
         ("1H", True): timedelta(minutes=2), ("1H", False): timedelta(hours=1)}
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


def in_session(now: datetime) -> bool:
    local = now.astimezone(VN)
    return local.weekday() < 5 and OPEN <= local.time() <= CLOSE


def _dec(value) -> Decimal | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return d if d.is_finite() and d > 0 else None


def _s(d: Decimal | None) -> str | None:
    return None if d is None else format(d.normalize(), "f")


def _row(symbol, kind, price, ref, *, ceiling=None, floor=None, high=None, low=None, volume=None, when=None) -> dict:
    change = price - ref if price is not None and ref is not None else None
    return {"symbol": symbol, "kind": kind, "price": _s(price), "ref": _s(ref), "change": _s(change) if change is None or change else "0",
            "change_pct": format((change / ref).quantize(Decimal("0.0001"), ROUND_HALF_UP), "f") if change is not None else None,
            "ceiling": _s(ceiling), "floor": _s(floor), "high": _s(high), "low": _s(low), "volume": volume, "time": when}


def _index_row(symbol: str, points: list[tuple[datetime, str]]) -> dict | None:
    if not points:
        return None
    last_time, last = points[-1]
    previous = [p for t, p in points if t.astimezone(VN).date() < last_time.astimezone(VN).date()]
    return _row(symbol, "index", _dec(last), _dec(previous[-1]) if previous else None, when=last_time.astimezone(VN).isoformat())


def build_board(symbols: list[str], *, board: Callable[[list[str]], list[dict]], index_minutes: Callable[[str], list[tuple[datetime, str]]],
                now: datetime) -> dict:
    rows, missing, errors = [], [], []
    for index in INDICES:
        try:
            row = _index_row(index, index_minutes(index))
        except Exception:
            row = None
            errors.append(f"Không đọc được {index} (nguồn lỗi)")
        rows.append(row) if row else missing.append(index)
    try:
        found = {str(r.get("symbol")).upper(): r for r in board(list(symbols))}
    except Exception:
        found = None
        errors.append("Không đọc được bảng giá cổ phiếu (nguồn lỗi)")
    for symbol in symbols if found is not None else []:
        r = found.get(symbol)
        if r is None:
            missing.append(symbol)
            continue
        k = lambda field: (_dec(r.get(field)) / THOUSAND) if _dec(r.get(field)) else None  # noqa: E731 - đồng to thousand đồng
        volume = r.get("accumulated_volume")
        rows.append(_row(symbol, "stock", k("match_price"), k("ref_price"), ceiling=k("ceiling"), floor=k("floor"), high=k("highest"),
                         low=k("lowest"), volume=int(volume) if isinstance(volume, (int, float)) and volume == volume else None,
                         when=str(r.get("trading_date") or "") or None))
    return {"as_of": now.isoformat(), "session_open": in_session(now), "rows": rows, "missing": missing, "errors": errors}


class ChartStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "chart"

    def _path(self, symbol: str, interval: str) -> Path:
        if not _SYMBOL.fullmatch(symbol) or interval not in INTERVALS:
            raise ValueError("invalid chart key")
        return self.root / f"{symbol}-{interval}.json"

    def read(self, symbol: str, interval: str) -> dict | None:
        path = self._path(symbol, interval)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, symbol: str, interval: str, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(symbol, interval)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record), encoding="utf-8")
        os.replace(tmp, path)


def _key(when: datetime, interval: str):
    """Daily bars by date; hourly bars as Vietnam wall-clock seconds, so the chart's axis reads in Hà Nội time."""
    local = when.astimezone(VN) if when.tzinfo else when
    if interval == "1D":
        return local.date().isoformat()
    return int(local.replace(tzinfo=timezone.utc).timestamp())


def _bars(raw: list[dict], interval: str) -> list[dict]:
    out = {}
    for r in raw:
        prices = [_dec(r.get(f)) for f in ("open", "high", "low", "close")]
        if any(p is None for p in prices) or prices[1] < max(prices) or prices[2] > min(prices):
            continue  # inconsistent row: dropped, never repaired
        when = r["time"] if isinstance(r["time"], datetime) else datetime.combine(r["time"], time()) if isinstance(r["time"], date) else None
        if when is None:
            continue
        o, h, lo, c = (_s(p) for p in prices)
        out[_key(when, interval)] = {"t": _key(when, interval), "o": o, "h": h, "l": lo, "c": c, "v": int(r.get("volume") or 0)}
    return [out[k] for k in sorted(out)]


def _indicators(bars: list[dict]) -> tuple[list[dict], list[dict]]:
    closes = [float(b["c"]) for b in bars]
    line, signal = macd(closes)
    strength = rsi(closes)
    m = [{"t": b["t"], "macd": round(a, 4), "signal": round(s, 4), "hist": round(a - s, 4)}
         for b, a, s in zip(bars, line, signal) if a is not None and s is not None]
    r = [{"t": b["t"], "v": round(v, 2)} for b, v in zip(bars, strength) if v is not None]
    return m, r


def chart(store: ChartStore, symbol: str, interval: str, *, fetch: Callable, now: datetime, index: bool) -> dict:
    saved = store.read(symbol, interval)
    fresh_for = FRESH[(interval, in_session(now))]
    if saved and now - datetime.fromisoformat(saved["fetched_at"]) < fresh_for:
        record, stale = saved, False
    else:
        try:
            bars = _bars(fetch(symbol, interval, (now - INTERVALS[interval]).astimezone(VN).date(), now.astimezone(VN).date(), index), interval)
            if not bars:
                raise ValueError("no bars")
            record, stale = {"symbol": symbol, "interval": interval, "bars": bars, "fetched_at": now.isoformat(), "source": "vnstock"}, False
            store.save(symbol, interval, record)
        except Exception:
            if not saved:
                return {"symbol": symbol, "interval": interval, "bars": [], "macd": [], "rsi": [], "fetched_at": None, "stale": False,
                        "reason": "Không đọc được dữ liệu nến (nguồn lỗi)"}
            record, stale = saved, True
    m, r = _indicators(record["bars"])
    return {"symbol": symbol, "interval": interval, "bars": record["bars"], "macd": m, "rsi": r, "fetched_at": record["fetched_at"],
            "stale": stale, "reason": None, "unit": "điểm" if index else "nghìn đồng"}
