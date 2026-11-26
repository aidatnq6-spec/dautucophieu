"""Giá dài hạn đã điều chỉnh: VNDirect's adjusted daily close (adClose, thousand đồng) since 2013 for every HOSE ticker.

VNDirect works the adjusted series out again after each bonus issue or stock dividend, so a ticker's whole series is fetched at once
and replaces what was stored. One public call per ticker (about 3,500 rows); every listed ticker is kept, not only watched ones.
A ticker never fetched comes first, then those not refreshed for a week, oldest first, up to the limit of the run. An empty answer
keeps what is stored; nothing is filled in.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

URL = ("https://api-finfo.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{symbol}~date:gte:" + "2013-01-01"
       + "&size=9999&fields=code,date,adClose")
SOURCE = "vndirect:finfo"
STALE = timedelta(days=7)
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


class PriceHistoryStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "price-history"

    def _path(self, symbol: str) -> Path:
        if not _SYMBOL.fullmatch(symbol or ""):
            raise ValueError("invalid symbol")
        return self.root / f"{symbol}.json"

    def read(self, symbol: str) -> dict | None:
        path = self._path(symbol)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, symbol: str, record: dict) -> None:
        path = self._path(symbol)
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


def parse_closes(text: str, *, symbol: str) -> list[list[str]]:
    days: dict[str, str] = {}
    for r in json.loads(text).get("data") or []:
        try:
            if r.get("code") != symbol or r.get("adClose") is None:
                continue
            day, close = str(r["date"])[:10], Decimal(str(r["adClose"]))
        except (InvalidOperation, KeyError, TypeError):
            continue
        if close.is_finite() and close > 0:
            days[day] = format(close.normalize(), "f")
    return [[d, days[d]] for d in sorted(days)]


def _due(store: PriceHistoryStore, symbols: list[str], now: datetime) -> list[str]:
    ages = []
    for s in symbols:
        record = store.read(s)
        when = datetime.fromisoformat(record["fetched_at"]) if record and record.get("fetched_at") else None
        if when is None or now - when >= STALE:
            ages.append((when is not None, when.isoformat() if when else "", s))
    return [s for _, _, s in sorted(ages)]


def sync_price_history(data_dir: Path, *, get: Callable[[str], str], now: datetime, symbols: list[str] | None = None, limit: int = 60,
                       sleep: Callable[[float], None] = time.sleep, pace: float = 0.5) -> dict:
    store = PriceHistoryStore(data_dir)
    if symbols:
        todo = [s.strip().upper() for s in symbols if _SYMBOL.fullmatch(s.strip().upper())]
        due = len(todo)
    else:
        listing = json.loads((Path(data_dir) / "hose-listing.json").read_text(encoding="utf-8")) if (Path(data_dir) / "hose-listing.json").is_file() else {}
        listed = [s for s in (listing.get("listing") or {}).get("symbols") or [] if _SYMBOL.fullmatch(str(s))]
        pending = _due(store, listed, now)
        due, todo = len(pending), pending[:max(0, limit)]
    updated = empty = 0
    failed: dict[str, str] = {}
    for i, symbol in enumerate(todo):
        if i:
            sleep(pace)
        try:
            closes = parse_closes(get(URL.format(symbol=symbol)), symbol=symbol)
        except Exception as exc:  # noqa: BLE001 - one ticker failing must not stop the run; it is reported
            failed[symbol] = type(exc).__name__
            continue
        if not closes:
            empty += 1
            continue
        store.save(symbol, {"symbol": symbol, "fetched_at": now.isoformat(), "source": SOURCE, "adjusted": True, "unit": "nghìn đồng",
                            "closes": closes})
        updated += 1
    return {"status": "partial" if failed else "ok", "due": due, "updated": updated, "empty": empty, "failed": failed}
