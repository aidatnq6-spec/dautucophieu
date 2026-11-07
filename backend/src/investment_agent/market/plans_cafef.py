"""Kế hoạch kinh doanh from CafeF's public ticker page data (one call per ticker; robots.txt of cafef.vn allows every agent,
checked 07/11/2026). CafeF gives the current year's plan only, so each year seen is kept. Amounts written in tỷ đồng ("210.000 tỷ",
"48.660,13 tỷ") are read; "N/A" and plans written in words (banks: "Tăng ~10%") are kept as written, never turned into numbers.
One JSON file per ticker under data/annual-plans-cafef (public data).
"""

import json
import os
import re
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from .leading import _get_with_retry

URL = "https://cafef.vn/du-lieu/Ajax/PageNew/KeHoachKinhDoanh.ashx?Symbol={symbol}"
NAMES = {"Doanh thu": "revenue", "Lợi nhuận trước thuế": "pbt", "Lợi nhuận sau thuế": "npat"}
MAX_AGE_DAYS, PACE_SECONDS = 7, 1.0
_AMOUNT = re.compile(r"^\s*([\d.]+(?:,\d+)?)\s*tỷ\s*$")
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


def _amount(text: str) -> str | None:
    m = _AMOUNT.match(text or "")
    if not m:
        return None
    try:
        d = Decimal(m.group(1).replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None
    return format(d.normalize(), "f") if d.is_finite() and d > 0 else None


def parse_plan(text: str, *, symbol: str) -> dict | None:
    data = (json.loads(text) or {}).get("Data") or {}
    if str(data.get("Symbol") or "").upper() != symbol or not data.get("Year"):
        return None
    raw = {str(v.get("Name")): str(v.get("Value")) for v in data.get("Values") or [] if v.get("Name")}
    figures = {key: _amount(raw.get(name, "")) for name, key in NAMES.items()}
    if all(v is None for v in figures.values()):
        return None
    return {"year": str(int(data["Year"])), **figures, "raw": raw}


class PlanStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, symbol: str) -> Path:
        if not _SYMBOL.fullmatch(symbol.upper()):
            raise ValueError("invalid symbol")
        return self.root / f"{symbol.upper()}.json"

    def read(self, symbol: str) -> dict | None:
        path = self._path(symbol)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(record["symbol"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


def sync_plans(store: PlanStore, symbols: list[str], *, get: Callable[[str], str], now: datetime, max_age_days: int = MAX_AGE_DAYS,
               sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """Refresh tickers not read for a week; one failing is reported and the others still update."""
    results = {}
    due = [s for s in symbols if (rec := store.read(s)) is None or (now - datetime.fromisoformat(rec["fetched_at"])).days >= max_age_days]
    for i, symbol in enumerate(due):
        if i:
            sleep(PACE_SECONDS)
        old = store.read(symbol) or {"symbol": symbol, "years": {}}
        try:
            plan = parse_plan(_get_with_retry(get, URL.format(symbol=symbol), sleep), symbol=symbol)
            years = dict(old.get("years", {}))
            if plan is not None:
                year = plan.pop("year")
                years[year] = {**plan, "read_on": now.date().isoformat()}
            store.save({"symbol": symbol, "fetched_at": now.isoformat(), "source": "cafef", "years": dict(sorted(years.items()))})
            results[symbol] = "ok" if plan is not None else "no_figures"
        except Exception as exc:  # one ticker never stops the others
            results[symbol] = f"error:{type(exc).__name__}"
    return results
