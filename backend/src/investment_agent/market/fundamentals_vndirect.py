"""The fundamentals record (market/fundamentals.py) built from VNDirect's public API, after Vnstock 6.0.0 (11/2026) dropped the
free statements it came from. Same shape and signs as before, so the valuation, Chất lượng báo cáo and dividends read it unchanged:

- years: parent profit, basic EPS (VNDirect line 23001) and equity; quarters: parent profit and equity, from the stored VNDirect
  statements (data/statements, or data/statements-financial for banks, securities firms and insurers);
- annual: the lines of Chất lượng báo cáo, costs (selling, admin) negative as Vnstock served them;
- dividends (cash per share), issues (stock dividends and bonus shares) and share_issues (with rights and placements as "raise"),
  from VNDirect's events, dated on their ex-rights day;
- shares_outstanding: VNDirect ratio 51004.

A line VNDirect lacks is left out; nothing is filled in.
"""

import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from .financial_ratios import kind_of
from .providers.vndirect_data import BASE, default_get, events as vndirect_events
from .sectors import load_sectors
from .statements import StatementStore

SHARES_URL = BASE + "ratios/latest?filter=itemCode:51004&where=code:{symbol}&order=reportDate&fields=itemCode,value,reportDate"
ANNUAL = {"revenue": "revenue", "gross_profit": "gross_profit", "selling": "selling", "admin": "admin", "npat": "profit", "total_assets": "total_assets",
          "current_assets": "current_assets", "current_liabilities": "current_liabilities", "long_liabilities": "long_liabilities",
          "receivables": "receivables", "cfo": "cfo"}
COSTS = ("selling", "admin")  # VNDirect: positive; Vnstock (and Chất lượng báo cáo): negative
BONUS, RAISE = ("STOCKDIV", "KINDDIV"), ("ISSUE",)


def _num(value) -> str | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return format(d.normalize(), "f") if d.is_finite() else None


def _ratio(percent) -> str | None:
    d = _num(percent)
    return _num(Decimal(d) / 100) if d is not None else None


def build_record(symbol: str, statements: dict, events: list[dict], *, shares: str | None, now: datetime) -> dict:
    years, quarters, annual = {}, {}, {}
    for y, row in (statements.get("years") or {}).items():
        years[y] = {k: row[src] for k, src in (("npat", "npat_parent"), ("eps", "eps"), ("equity", "equity")) if row.get(src) is not None}
        annual[y] = {}
        for src, name in ANNUAL.items():
            v = _num(row.get(src))
            if v is not None:
                annual[y][name] = _num(-Decimal(v)) if src in COSTS else v
    for q, row in (statements.get("quarters") or {}).items():
        quarters[q] = {k: row[src] for k, src in (("npat", "npat_parent"), ("equity", "equity")) if row.get(src) is not None}
    dividends, issues, share_issues = [], [], []
    for e in events:
        day, kind = (e.get("effectiveDate") or "")[:10], e.get("type")
        if not day:
            continue
        if kind == "DIVIDEND" and _num(e.get("dividend")):
            dividends.append({"date": day, "cash": _num(e["dividend"])})
        elif kind in BONUS:
            issues.append({"date": day, "ratio": _ratio(e.get("ratio"))})
            share_issues.append({"date": day, "kind": "bonus", "ratio": _ratio(e.get("ratio"))})
        elif kind in RAISE:
            share_issues.append({"date": day, "kind": "raise", "ratio": _ratio(e.get("ratio"))})
    return {"symbol": symbol, "fetched_at": now.isoformat(), "source": "vndirect:finfo", "years": years, "quarters": quarters, "annual": annual,
            "dividends": sorted(dividends, key=lambda d: d["date"]), "issues": sorted(issues, key=lambda d: d["date"]),
            "share_issues": sorted(share_issues, key=lambda d: d["date"]), "shares_outstanding": shares}


class VndirectFundamentals:
    """record(symbol, now) for sync_fundamentals; daily closes keep coming from the price provider."""

    def __init__(self, data_dir: Path, get: Callable[[str], str] = default_get, prices=None):
        self.data_dir, self.get, self.prices = Path(data_dir), get, prices

    def record(self, symbol: str, now: datetime) -> dict:
        sector = load_sectors(self.data_dir)[0].get(symbol)
        store = StatementStore(self.data_dir / ("statements" if kind_of(sector) is None else "statements-financial"))
        statements = store.read(symbol) or {}
        if not statements.get("years") and not statements.get("quarters"):
            raise LookupError("no stored VNDirect statements yet")
        events = vndirect_events(symbol, get=self.get, today=now.date(), years=10)
        rows = json.loads(self.get(SHARES_URL.format(symbol=symbol.upper()))).get("data", [])
        shares = next((_num(int(r["value"])) for r in rows if str(r.get("itemCode")) == "51004" and r.get("value")), None)
        return build_record(symbol, statements, events, shares=shares, now=now)

    def fetch_closes(self, symbol: str, start: date, end: date, *, interval: str, index: bool):
        from .providers.vnstock_adapter import VnstockProvider
        self.prices = self.prices or VnstockProvider()
        return self.prices.fetch_closes(symbol, start, end, interval=interval, index=index)
