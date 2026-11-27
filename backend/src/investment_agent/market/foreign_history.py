"""Khối ngoại theo phiên (owner, 27/11/2026, docs/superpowers/specs/2026-11-27-ngoai-tu-doanh-20-phien-design.md): foreign trading of
every HOSE stock from VNDirect's public v4/foreigns, one file per session under data/foreign, kept as tự doanh is (proprietary_history).

A session's foreign net is the sum over its stocks, as the brief's Khối ngoại line works it out; VNDirect's VNINDEX row is kept beside
(it counts more than the stocks) but is not that net. A session with no stock row is missing (VNDirect served 24/11/2026 with index
rows only); an empty figure leaves its ticker out, named, never 0.
"""

import json
import time
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from .proprietary_history import SOURCE, SessionStore, _plain, sync_sessions

URL = "https://api-finfo.vndirect.com.vn/v4/foreigns?q=floor:HOSE~tradingDate:{day}&size=9999"
_FIELDS = (("buy_volume", "buyVol"), ("sell_volume", "sellVol"), ("buy_value", "buyVal"), ("sell_value", "sellVal"))


class ForeignStore(SessionStore):
    folder = "foreign"


def parse_foreign_session(text: str, day: date) -> dict:
    rows = [r for r in json.loads(text).get("data") or [] if str(r.get("tradingDate"))[:10] == day.isoformat() and r.get("floor") == "HOSE"]
    stocks, skipped = {}, []
    for r in rows:
        if r.get("type") != "STOCK" or not r.get("code"):
            continue
        figures = {k: _plain(r.get(src)) for k, src in _FIELDS}
        if None in figures.values():
            skipped.append(str(r["code"]).upper())
        else:
            stocks[str(r["code"]).upper()] = figures
    if not stocks:
        return {"date": day.isoformat(), "thieu": True}
    if all(v == "0" for s in stocks.values() for v in s.values()):  # VNDirect's 23/11 and 28/08/2026: every stock 0, never a real session
        return {"date": day.isoformat(), "thieu": True, "ly_do": "VNDirect trả mọi mã bằng 0 cho phiên này"}
    out = {"date": day.isoformat(), "source": SOURCE, "stocks": stocks}
    index = next((r for r in rows if r.get("code") == "VNINDEX" and r.get("type") == "INDEX"), None)
    if index is not None:
        figures = {k: _plain(index.get(src)) for k, src in _FIELDS}
        if None not in figures.values():
            out["index"] = figures
    return {**out, "bo_qua": sorted(skipped)} if skipped else out


def sync_foreign(data_dir: Path, *, get: Callable[[str], str], now: datetime, sessions: list[date], limit: int = 260,
                 sleep: Callable[[float], None] = time.sleep, pace: float = 0.5) -> dict:
    return sync_sessions(ForeignStore(data_dir), url=URL, parse=parse_foreign_session, get=get, now=now, sessions=sessions, limit=limit,
                         sleep=sleep, pace=pace)
