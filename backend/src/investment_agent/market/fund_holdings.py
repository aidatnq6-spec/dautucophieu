"""What each open-ended fund holds, from Fmarket's public fund pages (the same source as fund_nav.py; robots.txt of api.fmarket.vn
answers 401, which RFC 9309 treats as no restriction, checked 06/11/2026).

Fmarket publishes, per fund and per month (productFund.updateAssetHoldingTime, e.g. "10/2026"): its ten largest stock holdings and
its largest bond holdings as a share of NAV, the split by asset kind and by sector. Only those published lines are kept: the rest of a
fund's portfolio is unknown here and nothing is filled in for it.

Every fund's page is read, not only the owner's, so nothing sent tells which funds the owner holds; a fund is read again only when
its month changes. Kept in data/fund-holdings.json (public data only).
"""

import json
import os
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .fund_nav import BODY, URL

DETAIL_URL = "https://api.fmarket.vn/res/products/{id}"
PACE_SECONDS = 0.5


class FundHoldingsStore:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "fund-holdings.json"

    def read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}

    def save(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)


def fund_holdings(data_dir: Path | None) -> dict[str, dict]:
    """{code: {as_of: "YYYY-MM", stocks, bonds, assets, industries}}; empty before the first sync."""
    return FundHoldingsStore(data_dir).read().get("funds", {}) if data_dir is not None else {}


def _pct(value) -> str | None:
    return format(Decimal(str(value)).normalize(), "f") if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _month(raw) -> str | None:
    parts = str(raw or "").strip().split("/")
    return f"{parts[1]}-{int(parts[0]):02d}" if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit() and len(parts[1]) == 4 else None


def parse_detail(data: dict, as_of: str) -> dict:
    stocks = [{"symbol": str(r["stockCode"]).strip().upper(), "percent": p, "industry": r.get("industry")}
              for r in data.get("productTopHoldingList") or [] if r.get("stockCode") and (p := _pct(r.get("netAssetPercent"))) is not None]
    bonds = [{"code": str(r["stockCode"]).strip().upper(), "percent": p, "industry": r.get("industry")}
             for r in data.get("productTopHoldingBondList") or [] if r.get("stockCode") and (p := _pct(r.get("netAssetPercent"))) is not None]
    assets = [{"kind": (r.get("assetType") or {}).get("code"), "name": (r.get("assetType") or {}).get("name"), "percent": p}
              for r in data.get("productAssetHoldingList") or [] if (p := _pct(r.get("assetPercent"))) is not None]
    industries = [{"name": r.get("industry"), "percent": p} for r in data.get("productIndustriesHoldingList") or []
                  if r.get("industry") and (p := _pct(r.get("assetPercent"))) is not None]
    return {"as_of": as_of, "stocks": stocks, "bonds": bonds, "assets": assets, "industries": industries}


def fund_holdings_sync(store: FundHoldingsStore, *, post: Callable[[str, dict], dict], get: Callable[[str], str], now: datetime,
                       sleep: Callable[[float], None] = time.sleep) -> dict:
    try:
        rows = (post(URL, BODY).get("data") or {}).get("rows") or []
    except Exception as exc:  # the list is down: keep what was stored
        return {"status": "error", "reason": type(exc).__name__}
    stored = store.read().get("funds", {})
    funds, fetched, unchanged, errors = dict(stored), 0, 0, {}
    for row in rows:
        code, month = str(row.get("shortName") or "").strip().upper(), _month((row.get("productFund") or {}).get("updateAssetHoldingTime"))
        if not code or not isinstance(row.get("id"), int) or month is None:
            continue
        if (stored.get(code) or {}).get("as_of") == month:
            unchanged += 1
            continue
        try:
            data = json.loads(get(DETAIL_URL.format(id=row["id"]))).get("data") or {}
            funds[code] = parse_detail(data, month)
            fetched += 1
        except Exception as exc:  # one fund failing keeps its stored month and the others
            errors[code] = type(exc).__name__
        sleep(PACE_SECONDS)
    if fetched:
        store.save({"source": "Fmarket", "fetched_at": now.isoformat(), "funds": funds})
    return {"status": "ok" if rows else "error", "fetched": fetched, "unchanged": unchanged, "errors": errors}
