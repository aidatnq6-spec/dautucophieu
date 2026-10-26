"""Statement figures, cash dividends and share issues per ticker (Vnstock free tier) for the reference valuation.

Only what the valuation needs is kept: parent-company profit after tax, basic EPS and equity, by year and by
quarter; cash dividends per share and share-issue ratios from company events (ex-right dates). Amounts are
decimal strings in đồng, one JSON file per ticker under data/fundamentals.
"""

import json
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

NPAT, EPS, EQUITY = "IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY", "IS_BASIC_EARNINGS_PER_SHARE", "BS_EQUITY"
_CASH = re.compile(r"tiền mặt.*?([\d][\d.,]*)\s*VND", re.I)
_RATIO = re.compile(r"tỉ lệ\s*([\d]+(?:[.,]\d+)?)\s*%", re.I)
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


def _num(value) -> str | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return format(d.normalize(), "f") if d.is_finite() else None


def _by_period(rows: list[dict], names: dict[str, str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for r in rows:
        key = names.get(str(r.get("id")))
        value = _num(r.get("value")) if key else None
        if value is not None:
            out.setdefault(str(r["period"]), {})[key] = value
    return dict(sorted(out.items()))


def _day(value) -> str | None:
    if value is None or str(value) in ("NaT", "nan", "None", ""):
        return None
    return value.date().isoformat() if hasattr(value, "date") else str(value)[:10]


def _events(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    dividends, issues = [], []
    for r in rows:
        day, title = _day(r.get("exright_date")), str(r.get("event_title_vi") or "")
        if day is None:
            continue
        if r.get("event_code") == "DIV" and (m := _CASH.search(title)):
            dividends.append({"date": day, "cash": _num(m.group(1).replace(",", "").replace(".", ""))})
        elif r.get("event_code") == "ISS" and (m := _RATIO.search(title)):
            issues.append({"date": day, "ratio": _num(Decimal(m.group(1).replace(",", ".")) / 100)})
    return sorted(dividends, key=lambda d: d["date"]), sorted(issues, key=lambda d: d["date"])


def build_record(symbol: str, frames: dict, fetched_at: datetime) -> dict:
    dividends, issues = _events(frames["events"])
    return {"symbol": symbol.upper(), "fetched_at": fetched_at.isoformat(), "source": "vnstock:vci",
            "years": _by_period(frames["income_year"] + frames["balance_year"], {NPAT: "npat", EPS: "eps", EQUITY: "equity"}),
            "quarters": _by_period(frames["income_quarter"] + frames["balance_quarter"], {NPAT: "npat", EQUITY: "equity"}),
            "dividends": dividends, "issues": issues}


class FundamentalsStore:
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

    def stale(self, symbols: list[str], *, now: datetime, max_age_days: int) -> list[str]:
        """Tickers to refresh: never fetched first, then the oldest beyond max_age_days."""
        ages = []
        for s in symbols:
            rec = self.read(s)
            fetched = datetime.fromisoformat(rec["fetched_at"]) if rec else None
            if fetched is None or (now - fetched).days >= max_age_days:
                ages.append((fetched is not None, fetched or now, s))
        return [s for _, _, s in sorted(ages)]
