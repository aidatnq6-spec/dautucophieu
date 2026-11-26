"""Giao dịch nội bộ và cổ đông lớn of a watched ticker: the notices HOSE publishes (insiders, their related persons, major
shareholders), as listed by VNDirect's public API v4/insider_trans (robots.txt allows all user agents, use=reference). Read when
the ticker page opens and kept in data/insider/<MÃ>.json for a day. Kind and volume are the source's; a notice without them stays
without them, and the original notice is one link away; what the HOSE document itself shows, read and checked by
insider_docs, fills them when it adds up (kept apart in data/insider-docs, never written over VNDirect's record). Public
disclosures; never sent to a model.
"""

import json
import os
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from .insider_docs import DocStore, fill_from_docs

URL = "https://api-finfo.vndirect.com.vn/v4/insider_trans?q=tagCodes:{symbol}&size=100&sort=newsDate:desc"
MAX_AGE = timedelta(days=1)
LINK = "https://dstock.vndirect.com.vn/"
NEWS_URL = "https://api-finfo.vndirect.com.vn/v4/news?q=newsId:{ids}&size={size}"
EXCHANGES = ("https://www.hsx.vn/", "https://hsx.vn/", "https://www.hnx.vn/", "https://hnx.vn/")
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


def _doc_links(payload: dict, get: Callable[[str], str]) -> dict[str, str]:
    """newsId → the exchange's notice, for the notices that give no kind or volume: insider_trans has no such link, v4/news has it.
    One call for all of them; a failing lookup leaves them without links."""
    ids = [str(r["newsId"]) for r in payload.get("data") or [] if r.get("newsId") is not None
           and (r.get("transType") not in KINDS or _shares(r.get("numberOfShares")) is None)]
    if not ids:
        return {}
    try:
        rows = json.loads(get(NEWS_URL.format(ids=",".join(ids), size=len(ids)))).get("data") or []
    except Exception:
        return {}
    return {str(r.get("newsId")): str(r.get("newsUrl") or "") for r in rows}


def _deals(symbol: str, payload: dict, links: dict[str, str] | None = None) -> list[dict]:
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
        doc = (links or {}).get(str(r.get("newsId")), "")  # the exchange's own notice, whose attached document holds the volumes
        out.append({"date": date, "kind": kind, "shares": _shares(r.get("numberOfShares")) if kind else None,
                    "source": r.get("newsSource"), "title": title, "url": url if url.startswith(LINK) else None,
                    "doc_url": doc if doc.startswith(EXCHANGES) else None})
    return sorted(out, key=lambda d: d["date"], reverse=True)


def _year(deals: list[dict], now: datetime) -> dict:
    """Done trades over the last 12 months (registrations are intentions); ESOP shares bought from the company, gifts between
    people, negotiated transfers and results without kind or volume counted apart."""
    since = (now.date() - timedelta(days=365)).isoformat()
    tally = {"since": since, "bought": 0, "buy_reports": 0, "sold": 0, "sell_reports": 0, "esop": 0, "esop_reports": 0,
             "gift_reports": 0, "transfer_reports": 0, "merged_reports": 0, "without_volume": 0}
    seen = set()
    for d in deals:
        if d["date"] < since or (d["kind"] or "").startswith("Đăng kí"):
            continue
        if d["kind"] is None or d["shares"] is None:
            tally["without_volume"] += 1
            continue
        # One trade in a major shareholder's own report and in its group's report (owner, 26/11/2026): same day, kind and shares count once
        key = (d["date"], d["kind"], d["shares"])
        if key in seen:
            tally["merged_reports"] += 1
            continue
        seen.add(key)
        if d["kind"] == "Mua":
            tally["bought"] += d["shares"]
            tally["buy_reports"] += 1
        elif d["kind"] == "Bán":
            tally["sold"] += d["shares"]
            tally["sell_reports"] += 1
        elif d["kind"] == "ESOP":
            tally["esop"] += d["shares"]
            tally["esop_reports"] += 1
        elif d["kind"] in ("Nhận chuyển nhượng", "Chuyển nhượng"):  # agreed between two parties, settled through VSDC
            tally["transfer_reports"] += 1
        else:  # Cho tặng, Nhận tặng
            tally["gift_reports"] += 1
    return tally


def _view(store: InsiderStore, record: dict, now: datetime, stale: bool) -> dict:
    deals = fill_from_docs(record["deals"], DocStore(store.root.parent))
    return {**record, "deals": deals, "year": _year(deals, now), "stale": stale, "reason": None}


def insider_deals(store: InsiderStore, symbol: str, *, get: Callable[[str], str], now: datetime) -> dict:
    saved = store.read(symbol)
    if saved and now - datetime.fromisoformat(saved["fetched_at"]) < MAX_AGE:
        return _view(store, saved, now, False)
    try:
        payload = json.loads(get(URL.format(symbol=symbol)))
        deals = _deals(symbol, payload, _doc_links(payload, get))
    except Exception:
        if saved:
            return _view(store, saved, now, True)
        return {"symbol": symbol, "deals": [], "year": None, "fetched_at": None, "stale": False,
                "reason": "Không đọc được thông báo giao dịch (nguồn VNDirect lỗi)"}
    record = {"symbol": symbol, "deals": deals, "fetched_at": now.isoformat(), "source": "vndirect:finfo"}
    store.save(symbol, record)
    return _view(store, record, now, False)
