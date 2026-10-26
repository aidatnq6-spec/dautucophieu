"""Trend board: MACD state and RSI over M, W, D1, H4, H1 for the owner's 17 instruments.

Closes come from Vnstock (Vietnamese stocks and indices), Coinbase public candles (BTC, PAXG as a
gold proxy) and FRED (dollar index, US 10-year, WTI; daily only). One snapshot per session, built
from the 15:30 slot on, is compared with the previous saved snapshot so changed cells can be
highlighted. Missing cells carry a reason; nothing is interpolated. Not a recommendation.
"""

import json
import os
import time as time_module
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from investment_agent.domain.pinned import CONFIG_DIR

from .indicators import four_hourly, macd_state, monthly, rsi_value, weekly
from .series import SeriesStore
from .trend_sources import coinbase_closes, ecb_dxy_closes, fred_closes
from .watchlist import load_watchlist

BOARD_PATH = CONFIG_DIR / "trend-board.json"
FRAMES = ("M", "W", "D1", "H4", "H1")
VN = timezone(timedelta(hours=7))
CLOSE = time(15, 30)
FULL_DAYS, REFRESH_DAYS, HOURLY_FULL_DAYS, HOURLY_REFRESH_DAYS = 2920, 60, 365, 30


def load_board(path: Path = BOARD_PATH) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["groups"]


def _version(path: Path = BOARD_PATH) -> str:
    return json.loads(Path(path).read_text(encoding="utf-8"))["version"]


def zone(value: int | None) -> str | None:
    return None if value is None else "overbought" if value >= 70 else "oversold" if value <= 30 else "neutral"


def _cell(closes: list[float] | None, reason: str | None = None) -> dict:
    if reason is None and not closes:
        reason = "Chưa có dữ liệu"
    if reason is not None:
        return {"macd": None, "rsi": None, "zone": None, "reason": reason}
    state, value = macd_state(closes), rsi_value(closes)
    # MACD needs more bars than RSI: a cell may show an RSI while its MACD is still "Chưa đủ lịch sử".
    return {"macd": state, "rsi": value, "zone": zone(value), "reason": None if state else "Chưa đủ lịch sử"}


def build_cells(daily, hourly, *, session_date: date | None, hourly_supported: bool) -> dict:
    """daily/hourly: (datetime, close) ascending. session_date set for Vietnamese rows: their last bar must be that day."""
    def fresh(points):
        return session_date is None or (bool(points) and points[-1][0].date() == session_date)
    d_reason = None if not daily or fresh(daily) else "Chưa có giá của phiên"
    cells = {"D1": _cell([v for _, v in daily or []], d_reason), "W": _cell(weekly(daily or []), d_reason),
             "M": _cell(monthly(daily or []), d_reason)}
    if not hourly_supported:  # separate dicts: compare() mutates each cell
        cells["H4"], cells["H1"] = _cell(None, "Nguồn chỉ có giá ngày"), _cell(None, "Nguồn chỉ có giá ngày")
    else:
        h_reason = None if not hourly or fresh(hourly) else "Chưa có giá của phiên"
        cells["H4"] = _cell(four_hourly(hourly or []), h_reason)
        cells["H1"] = _cell([v for _, v in hourly or []], h_reason)
    return {f: cells[f] for f in FRAMES}


def compare(snapshot: dict, previous: dict | None) -> dict:
    prev_cells = {r["id"]: r["cells"] for g in (previous or {}).get("groups", []) for r in g["rows"]}
    for g in snapshot["groups"]:
        for r in g["rows"]:
            for frame, c in r["cells"].items():
                p = prev_cells.get(r["id"], {}).get(frame) or {}
                macd_changed = bool(c["macd"] and p.get("macd") and c["macd"] != p["macd"])
                rsi_changed = bool(c["zone"] and p.get("zone") and c["zone"] != p["zone"])
                c.update({"macd_changed": macd_changed, "previous_macd": p.get("macd") if macd_changed else None,
                          "rsi_changed": rsi_changed, "previous_zone": p.get("zone") if rsi_changed else None})
    snapshot["previous_date"] = previous.get("session_date") if previous else None
    return snapshot


class SnapshotStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _files(self):
        return sorted(self.root.glob("????-??-??.json")) if self.root.is_dir() else []

    def save(self, snapshot: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{date.fromisoformat(snapshot['session_date']).isoformat()}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def _load(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def latest(self) -> dict | None:
        files = self._files()
        return self._load(files[-1]) if files else None

    def before(self, day: date) -> dict | None:
        """The most recent snapshot of an earlier session (normally the previous trading session)."""
        earlier = [p for p in self._files() if p.stem < day.isoformat()]
        return self._load(earlier[-1]) if earlier else None

    def prune(self, today: date, *, keep_days: int = 90) -> None:
        cutoff = (today - timedelta(days=keep_days)).isoformat()
        for p in self._files():
            if p.stem < cutoff:
                p.unlink()


def _retry(call, pause: float):
    """One retry after a short pause: Vnstock and the public feeds sometimes fail once and then answer."""
    try:
        return call()
    except Exception:
        time_module.sleep(pause)
        return call()


def _refresh(store: SeriesStore, key: str, fetch, *, today: date, full: int, refresh: int, enough: int, pause: float,
             fresh_through: date | None = None, pace: float = 0):
    points = store.read(key)
    if fresh_through is not None and points and points[-1][0].date() >= fresh_through:
        return  # already holds this session's bars (a later slot the same day)
    if pace:
        time_module.sleep(pace)  # Vnstock Community allows 60 calls a minute
    start = today - timedelta(days=full if len(points) < enough else refresh)
    store.upsert(key, _retry(lambda: fetch(start), pause))


def _board(data_dir: Path) -> list[dict]:
    """Configured groups, with the stock group following the watchlist (data/market-symbols.txt) when there is one."""
    groups, symbols = load_board(), load_watchlist(data_dir).symbols
    for g in groups:
        if g["id"] == "stocks" and symbols:
            g["rows"] = [{"id": s, "label": s, "source": {"kind": "vn", "index": False}} for s in symbols]
    return groups


def run_trend(data_dir: Path, cal, *, now: datetime, provider, get, pause: float = 65.0, pace: float = 1.5) -> dict:
    """pause: wait before the single retry (long enough to clear Vnstock's per-minute limit); pace: gap between Vnstock calls."""
    local = now.astimezone(VN)
    today = local.date()
    try:
        if not cal.is_session(today):
            return {"status": "skipped", "reason": "not_a_session"}
    except ValueError:
        return {"status": "skipped", "reason": "calendar_missing"}
    if local.time() < CLOSE:
        return {"status": "skipped", "reason": "before_close"}
    data_dir = Path(data_dir)
    days, hours = SeriesStore(data_dir / "trend-sources"), SeriesStore(data_dir / "intraday")
    errors: dict[str, str] = {}
    groups = []
    for group in _board(data_dir):
        rows = []
        for row in group["rows"]:
            src, rid = row["source"], row["id"]
            try:
                if src["kind"] == "vn":
                    _refresh(days, f"{rid}-1d", lambda s: provider.fetch_closes(rid, s, today, interval="1D", index=src["index"]),
                             today=today, full=FULL_DAYS, refresh=REFRESH_DAYS, enough=400, pause=pause, fresh_through=today, pace=pace)
                    _refresh(hours, f"{rid}-1h", lambda s: provider.fetch_closes(rid, s, today, interval="1H", index=src["index"]),
                             today=today, full=HOURLY_FULL_DAYS, refresh=HOURLY_REFRESH_DAYS, enough=1, pause=pause, fresh_through=today,
                             pace=pace)
                    cells = build_cells(days.read(f"{rid}-1d"), hours.read(f"{rid}-1h"), session_date=today, hourly_supported=True)
                elif src["kind"] == "coinbase":
                    _refresh(days, f"{rid}-1d", lambda s: coinbase_closes(get, src["product"], 86400, s, today),
                             today=today, full=FULL_DAYS, refresh=REFRESH_DAYS, enough=400, pause=pause)
                    _refresh(hours, f"{rid}-1h", lambda s: coinbase_closes(get, src["product"], 3600, s, today),
                             today=today, full=REFRESH_DAYS, refresh=7, enough=1, pause=pause)
                    cells = build_cells(days.read(f"{rid}-1d"), hours.read(f"{rid}-1h"), session_date=None, hourly_supported=True)
                elif src["kind"] == "ecb_dxy":
                    # Own series key: the row used FRED's broad dollar index before, a different level that must not be mixed in.
                    key = f"{rid}-ecb-1d"
                    days.upsert(key, _retry(lambda: ecb_dxy_closes(get, have=len(days.read(key))), pause))
                    cells = build_cells(days.read(key), None, session_date=None, hourly_supported=False)
                elif src["kind"] == "fred":
                    days.upsert(f"{rid}-1d", _retry(lambda: fred_closes(get, src["series"], today - timedelta(days=FULL_DAYS)), pause))
                    cells = build_cells(days.read(f"{rid}-1d"), None, session_date=None, hourly_supported=False)
                else:
                    cells = {f: _cell(None, src["reason"]) for f in FRAMES}
            except Exception as exc:  # one failing source never stops the board
                errors[rid] = f"error:{type(exc).__name__}"
                cells = {f: _cell(None, "Lỗi nguồn") for f in FRAMES}
            rows.append({"id": rid, "label": row["label"], "note": row.get("note"), "cells": cells})
        groups.append({"id": group["id"], "label": group["label"], "rows": rows})
    store = SnapshotStore(data_dir / "trend")
    snapshot = compare({"session_date": today.isoformat(), "generated_at": now.astimezone(timezone.utc).isoformat(),
                        "board_version": _version(), "errors": errors, "groups": groups}, store.before(today))
    store.save(snapshot)
    store.prune(today)
    return {"status": "ok", "session_date": today.isoformat(), "errors": errors}
