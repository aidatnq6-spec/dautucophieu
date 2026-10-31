"""Cổ đông lớn và ban lãnh đạo of a watched ticker (Vnstock free tier: VCI holders, officers and foreign/state stakes; KBS owner types), read when the ticker page opens and
kept in data/company/<MÃ>.json for 30 days. When the source fails, the saved copy is shown with its date; with no copy,
a reason. Public company disclosures; never sent to a model.
"""

import json
import os
import re
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable

MAX_AGE = timedelta(days=30)
SCHEMA = 2  # 2 adds foreign/state ownership and the owner-type structure; older files are read again
TOP = 10
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


def _others(holders: list[dict]) -> str | None:
    """1 − the ten largest stakes (as the page lists them); None when one of them has no figure or the stakes exceed 100%."""
    top = sorted(holders, key=lambda h: (h["percent"] is None, -(h["percent"] or 0)))[:TOP]
    if not top or any(h["percent"] is None for h in top):
        return None
    rest = Decimal(1) - sum(Decimal(str(h["percent"])) for h in top)
    return None if rest < 0 else format(rest.normalize(), "f") if rest else "0"


def _latest(holders: list[dict]) -> list[dict]:
    """The source keeps older disclosures of the same holder; one row per name, the latest dated one (undated counts as oldest)."""
    keep: dict[str, dict] = {}
    for h in holders:
        name = " ".join(h["name"].split()).casefold()
        if name not in keep or (h["updated"] or "") > (keep[name]["updated"] or ""):
            keep[name] = h
    return list(keep.values())


def _view(record: dict, *, stale: bool) -> dict:
    holders = _latest(record["shareholders"])
    return {"ownership": None, "structure": None, **record, "shareholders": holders, "others_percent": _others(holders), "stale": stale,
            "reason": None}


def company_people(store: PeopleStore, symbol: str, *, fetch: Callable[[str], dict], now: datetime) -> dict:
    saved = store.read(symbol)
    if saved and saved.get("schema") == SCHEMA and now - datetime.fromisoformat(saved["fetched_at"]) < MAX_AGE:
        return _view(saved, stale=False)
    try:
        fresh = fetch(symbol)
    except Exception:
        if saved:
            return _view(saved, stale=True)
        return {"symbol": symbol, "shareholders": [], "officers": [], "ownership": None, "structure": None, "others_percent": None,
                "fetched_at": None, "stale": False, "reason": "Không đọc được dữ liệu cổ đông (nguồn lỗi)"}
    record = {"schema": SCHEMA, "symbol": symbol, "shareholders": fresh["shareholders"], "officers": fresh["officers"],
              "ownership": fresh.get("ownership"), "structure": fresh.get("structure"), "fetched_at": now.isoformat(), "source": "vnstock:vci,kbs"}
    store.save(symbol, record)
    return _view(record, stale=False)
