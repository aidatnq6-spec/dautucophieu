"""Tự doanh theo phiên (owner, 27/11/2026, docs/superpowers/specs/2026-11-27-tu-doanh-mcp-design.md): HOSE proprietary trading from
VNDirect's public v4/proprietary_trading, one file per session under data/proprietary, about a year kept, for the MCP tool tu_doanh.

Each session keeps the VNINDEX row and every HOSE stock row as served (đồng, shares), and whether the stocks add up to the VNINDEX row.
A session VNDirect has not posted is kept as missing: asked again while it is among the last 20 sessions (VNDirect posts some sessions
late), asked once when older. Another session never stands in for one.
"""

import json
import os
import re
import time
from datetime import date, datetime, timedelta
from datetime import time as dtime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

URL = "https://api-finfo.vndirect.com.vn/v4/proprietary_trading?q=floor:HOSE~date:{day}&size=9999"
SOURCE = "vndirect:finfo"
RETRY_SESSIONS = 20
KEEP_DAYS = 400  # 250 sessions take about 365 days, and VNDirect posts some sessions late
VN = ZoneInfo("Asia/Ho_Chi_Minh")
CLOSED_AT = dtime(15, 0)
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FIELDS = (("buy_volume", "buyingVol"), ("sell_volume", "sellingVol"), ("buy_value", "buyingVal"), ("sell_value", "sellingVal"))


def _plain(value) -> str | None:
    """A figure as served, plain digits; None when VNDirect left it empty or unreadable (never stored as 0)."""
    if value is None:
        return None
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        return None
    return format(d.normalize(), "f") if d.is_finite() else None


class ProprietaryStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "proprietary"

    def _path(self, day) -> Path:
        key = day.isoformat() if isinstance(day, date) else str(day)
        if not _DAY.fullmatch(key):
            raise ValueError("invalid day")
        return self.root / f"{key}.json"

    def read(self, day) -> dict | None:
        path = self._path(day)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(record["date"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def days(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.json") if _DAY.fullmatch(p.stem)) if self.root.is_dir() else []

    def prune(self, before: date) -> None:
        for day in self.days():
            if day < before.isoformat():
                self._path(day).unlink(missing_ok=True)


def parse_session(text: str, day: date) -> dict:
    rows = [r for r in json.loads(text).get("data") or [] if str(r.get("date"))[:10] == day.isoformat() and r.get("floor") == "HOSE"]
    index = next((r for r in rows if r.get("code") == "VNINDEX" and r.get("type") == "INDEX"), None)
    if index is None:
        return {"date": day.isoformat(), "thieu": True}
    total = {k: _plain(index.get(src)) for k, src in _FIELDS}
    if None in total.values():
        return {"date": day.isoformat(), "thieu": True, "ly_do": "Dòng VNINDEX của VNDirect thiếu số mua hoặc bán"}
    stocks, skipped = {}, []
    for r in rows:
        if r.get("type") != "STOCK" or not r.get("code"):
            continue
        figures = {k: _plain(r.get(src)) for k, src in _FIELDS}
        if None in figures.values():
            skipped.append(str(r["code"]).upper())  # left out of every sum and named, never counted as 0
        else:
            stocks[str(r["code"]).upper()] = figures
    adds_up = all(sum((Decimal(s[k]) for s in stocks.values()), Decimal(0)) == Decimal(total[k]) for k in ("buy_value", "sell_value"))
    out = {"date": day.isoformat(), "source": SOURCE, "index": total, "stocks": stocks, "khop": bool(stocks) and adds_up and not skipped}
    return {**out, "bo_qua": sorted(skipped)} if skipped else out


def sync_proprietary(data_dir: Path, *, get: Callable[[str], str], now: datetime, sessions: list[date], limit: int = 260,
                     sleep: Callable[[float], None] = time.sleep, pace: float = 0.5) -> dict:
    """sessions: HOSE sessions of the window, any order. Newest first; one call per session."""
    store, local = ProprietaryStore(data_dir), now.astimezone(VN)
    newest = sorted((d for d in set(sessions) if d < local.date() or (d == local.date() and local.time() >= CLOSED_AT)), reverse=True)
    recent = set(newest[:RETRY_SESSIONS])
    due = []
    for day in newest:
        record = store.read(day)
        if record is None or (record.get("thieu") and day in recent):
            due.append(day)
    fetched = missing = 0
    failed: dict[str, str] = {}
    for i, day in enumerate(due[:max(0, limit)]):
        if i:
            sleep(pace)
        try:
            record = parse_session(get(URL.format(day=day.isoformat())), day)
        except Exception as exc:  # noqa: BLE001 - one session failing never stops the others; it is reported
            failed[day.isoformat()] = f"error:{type(exc).__name__}"
            continue
        store.save({**record, "fetched_at" if not record.get("thieu") else "hoi_luc": now.isoformat()})
        if record.get("thieu"):
            missing += 1
        else:
            fetched += 1
    store.prune(local.date() - timedelta(days=KEEP_DAYS))
    return {"status": "partial" if failed else "ok", "due": len(due), "fetched": fetched, "missing": missing, "failed": failed}
