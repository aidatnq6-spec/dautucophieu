"""NAV/đơn vị of Vietnamese open-ended funds from Fmarket's public fund list: one call for every fund (about 70), each with its
valuation date (extra.lastNAVDate). Nothing about the owner is sent — the request names no fund. robots.txt of api.fmarket.vn answers 401,
which RFC 9309 treats as no restriction (checked 06/11/2026). Fmarket is a distributor, not the fund manager: the page says so.

Kept in data/fund-nav.json (public data only). A failed or empty answer keeps what was stored; a fund missing from a later answer
keeps its old NAV with its old date. Each fund's kind (STOCK, BOND, BALANCED), manager, management fee and Fmarket's returns over
set periods are kept beside it (a period Fmarket leaves out stays blank), and every NAV seen is added to data/fund-nav-history.json,
one point per fund per valuation day, so a history builds up from the first sync."""

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


def fund_profiles(data_dir: Path | None) -> dict[str, dict]:
    """{code: {kind, manager, fee, returns: {ytd, m1, m3, m6, m12, m36, m60, annual36}}} as percentages in strings, None when missing."""
    return FundNavStore(data_dir).read().get("profiles", {}) if data_dir is not None else {}


def fund_history(data_dir: Path | None) -> dict[str, dict[str, str]]:
    """{code: {valuation date: NAV}} of every sync since the history began."""
    path = Path(data_dir) / HISTORY_FILE if data_dir is not None else None
    return json.loads(path.read_text(encoding="utf-8")) if path is not None and path.is_file() else {}


HISTORY_FILE = "fund-nav-history.json"
_RETURNS = {"ytd": "navToLastYear", "m1": "navTo1Months", "m3": "navTo3Months", "m6": "navTo6Months", "m12": "navTo12Months",
            "m36": "navTo36Months", "m60": "navTo60Months", "annual36": "annualizedReturn36Months"}


def _number(value) -> str | None:
    return format(Decimal(str(value)).normalize(), "f") if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _profile(row: dict) -> dict:
    change = row.get("productNavChange") or {}
    kind = str((row.get("dataFundAssetType") or {}).get("code") or "").upper() or None
    return {"kind": kind, "manager": ((row.get("owner") or {}).get("shortName") or "").strip() or None, "fee": _number(row.get("managementFee")),
            "returns": {key: _number(change.get(field)) for key, field in _RETURNS.items()}}


def _profiles(answer: dict) -> dict[str, dict]:
    return {str(r["shortName"]).strip().upper(): _profile(r) for r in (answer.get("data") or {}).get("rows") or [] if r.get("shortName")}


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
        answer = post(URL, BODY)
        funds, profiles = _parse(answer), _profiles(answer)
    except Exception as exc:  # the source is down or changed: keep the stored NAVs
        return {"status": "error", "reason": type(exc).__name__}
    if not funds:
        return {"status": "error", "reason": "empty"}
    stored = store.read()
    store.save({"source": "Fmarket", "url": URL, "fetched_at": now.isoformat(), "funds": {**stored.get("funds", {}), **funds},
                "profiles": {**stored.get("profiles", {}), **{c: p for c, p in profiles.items() if c in funds}}})
    history = fund_history(store.path.parent)
    for code, fund in funds.items():
        history.setdefault(code, {})[fund["date"]] = fund["nav"]
    path = store.path.parent / HISTORY_FILE
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(history, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)
    return {"status": "ok", "funds": len(funds)}
