"""Cổ đông lớn và ban lãnh đạo of a watched ticker (Vnstock free tier, VCI source), read when the ticker page opens and
kept in data/company/<MÃ>.json for 30 days. When the source fails, the saved copy is shown with its date; with no copy,
a reason. Public company disclosures; never sent to a model.
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

MAX_AGE = timedelta(days=30)
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


class PeopleStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "company"

    def _path(self, symbol: str) -> Path:
        if not _SYMBOL.fullmatch(symbol):
            raise ValueError("invalid symbol")
        return self.root / f"{symbol}.json"

    def read(self, symbol: str) -> dict | None:
        path = self._path(symbol)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, symbol: str, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(symbol)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


def company_people(store: PeopleStore, symbol: str, *, fetch: Callable[[str], dict], now: datetime) -> dict:
    saved = store.read(symbol)
    if saved and now - datetime.fromisoformat(saved["fetched_at"]) < MAX_AGE:
        return {**saved, "stale": False, "reason": None}
    try:
        fresh = fetch(symbol)
    except Exception:
        if saved:
            return {**saved, "stale": True, "reason": None}
        return {"symbol": symbol, "shareholders": [], "officers": [], "fetched_at": None, "stale": False,
                "reason": "Không đọc được dữ liệu cổ đông (nguồn lỗi)"}
    record = {"symbol": symbol, "shareholders": fresh["shareholders"], "officers": fresh["officers"], "fetched_at": now.isoformat(),
              "source": "vnstock:vci"}
    store.save(symbol, record)
    return {**record, "stale": False, "reason": None}
