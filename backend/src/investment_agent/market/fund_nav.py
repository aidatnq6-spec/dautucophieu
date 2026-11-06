"""NAV/đơn vị of Vietnamese open-ended funds from Fmarket's public fund list: one call for every fund (about 70), each with its
valuation date (extra.lastNAVDate). Nothing about the owner is sent — the request names no fund. robots.txt of api.fmarket.vn answers 401,
which RFC 9309 treats as no restriction (checked 06/11/2026). Fmarket is a distributor, not the fund manager: the page says so.

Kept in data/fund-nav.json (public data only). A failed or empty answer keeps what was stored; a fund missing from a later answer
keeps its old NAV with its old date."""

import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable

URL = "https://api.fmarket.vn/res/products/filter"
BODY = {"types": ["NEW_FUND", "TRADING_FUND"], "issuerIds": [], "sortOrder": "DESC", "sortField": "navTo6Months", "page": 1, "pageSize": 200,
        "isIpo": False, "fundAssetTypes": [], "bondRemainPeriods": [], "searchField": "", "isBuyByReward": False, "thirdAppIds": []}
VN = timezone(timedelta(hours=7))


class FundNavStore:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "fund-nav.json"

    def read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}

    def save(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)


def fund_navs(data_dir: Path | None) -> dict[str, dict]:
    """{code: {name, nav, date}}; empty without a data dir or before the first sync."""
    return FundNavStore(data_dir).read().get("funds", {}) if data_dir is not None else {}


def _parse(answer: dict) -> dict[str, dict]:
    funds = {}
    for row in (answer.get("data") or {}).get("rows") or []:
        code, nav, ms = row.get("shortName"), row.get("nav"), (row.get("extra") or {}).get("lastNAVDate")
        if not code or not isinstance(nav, (int, float)) or nav <= 0 or not isinstance(ms, (int, float)):
            continue  # no NAV yet (a new fund): left out, never 0
        funds[code.strip().upper()] = {"name": (row.get("name") or "").strip(), "nav": format(Decimal(str(nav)).normalize(), "f"),
                                       "date": datetime.fromtimestamp(ms / 1000, VN).date().isoformat()}
    return funds


def fund_nav_sync(store: FundNavStore, *, post: Callable[[str, dict], dict], now: datetime) -> dict:
    try:
        funds = _parse(post(URL, BODY))
    except Exception as exc:  # the source is down or changed: keep the stored NAVs
        return {"status": "error", "reason": type(exc).__name__}
    if not funds:
        return {"status": "error", "reason": "empty"}
    old = store.read().get("funds", {})
    store.save({"source": "Fmarket", "url": URL, "fetched_at": now.isoformat(), "funds": {**old, **funds}})
    return {"status": "ok", "funds": len(funds)}
