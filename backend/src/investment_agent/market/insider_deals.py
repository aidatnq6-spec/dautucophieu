"""Giao dịch nội bộ và cổ đông lớn of a watched ticker: the notices HOSE publishes (insiders, their related persons, major
shareholders), as listed by VNDirect's public API v4/insider_trans (robots.txt allows all user agents, use=reference). Read when
the ticker page opens and kept in data/insider/<MÃ>.json for a day. Kind and volume are the source's; a notice without them stays
without them, and the original notice is one link away. Public disclosures; never sent to a model.
"""

import json
import os
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

URL = "https://api-finfo.vndirect.com.vn/v4/insider_trans?q=tagCodes:{symbol}&size=100&sort=newsDate:desc"
MAX_AGE = timedelta(days=1)
LINK = "https://dstock.vndirect.com.vn/"
KINDS = {"Mua", "Bán", "Đăng kí mua", "Đăng kí bán"}
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


class InsiderStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "insider"

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


def _shares(value) -> int | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return int(d) if d.is_finite() and d > 0 and d == d.to_integral_value() else None


def _deals(symbol: str, payload: dict) -> list[dict]:
    out = []
    for r in payload.get("data") or []:
        if symbol not in str(r.get("tagCodes") or "").upper().replace(" ", "").split(","):
            continue
        date = str(r.get("newsDate") or "")[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            continue
        kind = r.get("transType") if r.get("transType") in KINDS else None
        title = str(r.get("newsTitle") or "").strip()
        title = title[len(symbol) + 1:].strip() if title.upper().startswith(symbol + ":") else title
        url = str(r.get("dstockUrl") or "")
        out.append({"date": date, "kind": kind, "shares": _shares(r.get("numberOfShares")) if kind else None,
                    "source": r.get("newsSource"), "title": title, "url": url if url.startswith(LINK) else None})
    return sorted(out, key=lambda d: d["date"], reverse=True)


def _year(deals: list[dict], now: datetime) -> dict:
    """Done trades over the last 12 months (registrations are intentions); results without kind or volume counted apart."""
    since = (now.date() - timedelta(days=365)).isoformat()
    tally = {"since": since, "bought": 0, "buy_reports": 0, "sold": 0, "sell_reports": 0, "without_volume": 0}
    for d in deals:
        if d["date"] < since or (d["kind"] or "").startswith("Đăng kí"):
            continue
        if d["kind"] is None or d["shares"] is None:
            tally["without_volume"] += 1
        elif d["kind"] == "Mua":
            tally["bought"] += d["shares"]
            tally["buy_reports"] += 1
        else:
            tally["sold"] += d["shares"]
            tally["sell_reports"] += 1
    return tally


def insider_deals(store: InsiderStore, symbol: str, *, get: Callable[[str], str], now: datetime) -> dict:
    saved = store.read(symbol)
    if saved and now - datetime.fromisoformat(saved["fetched_at"]) < MAX_AGE:
        return {**saved, "year": _year(saved["deals"], now), "stale": False, "reason": None}
    try:
        deals = _deals(symbol, json.loads(get(URL.format(symbol=symbol))))
    except Exception:
        if saved:
            return {**saved, "year": _year(saved["deals"], now), "stale": True, "reason": None}
        return {"symbol": symbol, "deals": [], "year": None, "fetched_at": None, "stale": False,
                "reason": "Không đọc được thông báo giao dịch (nguồn VNDirect lỗi)"}
    record = {"symbol": symbol, "deals": deals, "fetched_at": now.isoformat(), "source": "vndirect:finfo"}
    store.save(symbol, record)
    return {**record, "year": _year(deals, now), "stale": False, "reason": None}
