"""The session's shape for the brief, in numbers only: VN-Index's range (high, low, close and how far the close sits from each), the
run of sessions in the same direction, matched volume against the previous session and the 20 before, and HOSE's published value
against the same. Nothing is judged and nothing is estimated: a missing bar or figure is named, never filled.

The daily bars are KBS's (vnstock), whose high and low may include the reference level before the opening match; the page says so.
"""

import json
import os
from datetime import date
from pathlib import Path
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Callable

BASE = 20
_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")
HOSE_VALUE = "https://api.hsx.vn/mk/api/v1/market/foreign-trading-value-report?fromDate={start}&toDate={end}"
MIN_SESSIONS = 15  # of the 20 before, with a figure, for an average (fix 25/11/2026)


def _s(value: Decimal, q: Decimal) -> str:
    return str(value.quantize(q, ROUND_HALF_UP))


def _missing(reason: str) -> dict:
    return {"status": "missing", "reason": reason}


def _streak(bars: dict, chain: list[date]) -> dict:
    """chain: the session then earlier sessions, newest first."""
    close = lambda d: bars[d]["close"]
    if len(chain) < 2 or not bars.get(chain[1]):
        return {"direction": None, "sessions": 0, "at_least": True, "change": None, "pct": None}
    first = close(chain[0]) - close(chain[1])
    if first == 0:
        return {"direction": "flat", "sessions": 1, "at_least": False, "change": "0.00", "pct": "0.0000"}
    up, n = first > 0, 1
    while True:
        if n + 1 >= len(chain) or not bars.get(chain[n + 1]):
            return {"direction": "up" if up else "down", "sessions": n, "at_least": True, "change": None, "pct": None}
        step = close(chain[n]) - close(chain[n + 1])
        if step == 0 or (step > 0) != up:
            break
        n += 1
    base = close(chain[n])
    change = close(chain[0]) - base
    return {"direction": "up" if up else "down", "sessions": n, "at_least": False, "change": _s(change, _Q2), "pct": _s(change / base, _Q4)}


def _volume(bars: dict, session_date: date, earlier: list[date]) -> dict:
    window = earlier[-BASE:]
    lacking = BASE - sum(1 for d in window if bars.get(d))
    if lacking:
        return _missing(f"Thiếu nến {lacking} trong {BASE} phiên trước")
    today, previous = bars[session_date]["volume"], bars[window[-1]]["volume"]
    avg = Decimal(sum(bars[d]["volume"] for d in window)) / BASE
    return {"status": "ok", "today": today, "previous": previous,
            "change_pct": _s(Decimal(today) / previous - 1, _Q4) if previous else None,
            "avg20": int(avg.quantize(Decimal(1), ROUND_HALF_UP)), "ratio20": _s(Decimal(today) / avg, _Q2) if avg else None}


def _ma20(bars: dict, session_date: date, earlier: list[date]) -> dict:
    """Mean close of the session and the 19 before it; a missing bar is named, never filled."""
    days = [*earlier[-(BASE - 1):], session_date]
    lacking = BASE - sum(1 for d in days if bars.get(d))
    if lacking:
        return _missing(f"Thiếu nến {lacking} trong {BASE} phiên")
    value = sum((bars[d]["close"] for d in days), Decimal(0)) / BASE
    return {"status": "ok", "value": _s(value, _Q2), "above": bars[session_date]["close"] > value}


def index_session(bars: dict[date, dict | None], *, session_date: date, earlier: list[date]) -> dict:
    """bars: VN-Index daily bars by session (high, low, close as Decimal; volume in shares); earlier: the sessions before
    session_date on the trading calendar, ascending."""
    today = bars.get(session_date)
    if not today:
        return _missing("Chưa có nến VN-Index phiên này")
    high, low, close = today["high"], today["low"], today["close"]
    return {"status": "ok",
            "range": {"high": _s(high, _Q2), "low": _s(low, _Q2), "close": _s(close, _Q2), "from_high": _s(high - close, _Q2),
                      "from_low": _s(close - low, _Q2)},
            "streak": _streak(bars, [session_date, *reversed(earlier)]),
            "volume": _volume(bars, session_date, earlier), "ma20": _ma20(bars, session_date, earlier)}


def _hose_value_bn(raw: str) -> Decimal | None:
    """HOSE's market value (million đồng) in billions, or None when HOSE has nothing for those dates."""
    rows = {r["trading_type_name"]: r for r in json.loads(raw).get("data") or []}
    if "Mua" not in rows:
        return None
    return Decimal(str(rows["Mua"]["market_value"]).replace(",", "").strip()) / 1000


def _read_cache(path: Path | None) -> dict:
    if path is None or not Path(path).is_file():
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_cache(path: Path | None, cache: dict) -> None:
    if path is None:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(sorted(cache.items())), ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def hose_liquidity(hose: dict, *, earlier: list[date], hose_get: Callable[[str], str], cache_path: Path | None = None,
                   today: date | None = None, pause: Callable[[], None] = lambda: None) -> dict:
    """HOSE's published value (with put-through deals) against the previous session that has a figure and the average of the 20 sessions
    before that have one. Each session is asked on its own and kept in `cache_path` (fix 25/11/2026: HOSE has no figure for 24/11/2026,
    and a range's total over 19 days was divided by 20); a session without a figure is asked again at most once a day. Fewer than
    MIN_SESSIONS of the 20 with a figure: no average, named, never filled."""
    if hose.get("status") != "ok":
        return _missing(hose.get("reason") or "HOSE chưa công bố")
    if len(earlier) < BASE:
        return _missing(f"Lịch giao dịch chưa đủ {BASE} phiên trước")
    window, cache, checked = earlier[-BASE:], _read_cache(cache_path), (today or date.today()).isoformat()
    values: dict[date, Decimal | None] = {}
    try:
        for d in window:
            kept = cache.get(d.isoformat())
            if kept and (kept.get("value_bn") is not None or kept.get("checked") == checked):
                values[d] = Decimal(kept["value_bn"]) if kept.get("value_bn") is not None else None
                continue
            pause()  # between days asked: the first run asks up to 20
            got = _hose_value_bn(hose_get(HOSE_VALUE.format(start=d.isoformat(), end=d.isoformat())))
            values[d] = got
            cache[d.isoformat()] = {"value_bn": None if got is None else format(got.normalize(), "f"), "checked": checked}
    except (ValueError, KeyError, TypeError, InvalidOperation):
        _write_cache(cache_path, cache)
        return _missing("HOSE đổi định dạng")
    _write_cache(cache_path, cache)
    with_figure = [d for d in window if values.get(d)]
    if not with_figure:
        return _missing("HOSE chưa có số các phiên trước")
    if len(with_figure) < MIN_SESSIONS:
        return _missing(f"HOSE chỉ có số {len(with_figure)}/{BASE} phiên trước")
    previous_day = with_figure[-1]
    previous, avg = values[previous_day], sum((values[d] for d in with_figure), Decimal(0)) / len(with_figure)
    today_value = Decimal(hose["total_value_bn"])
    return {"status": "ok", "today_bn": _s(today_value, _Q2), "previous_bn": _s(previous, _Q2), "previous_session": previous_day.isoformat(),
            "previous_skipped": previous_day != window[-1],
            "change_pct": _s(today_value / previous - 1, _Q4), "avg20_bn": _s(avg, _Q2), "avg_sessions": len(with_figure),
            "ratio20": _s(today_value / avg, _Q2)}
