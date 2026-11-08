"""Full financial statements of watched non-financial companies from VNDirect's public statements API, for Bảng số tài chính.

The free Vnstock tier keeps eight periods and has no interest expense, depreciation, borrowings or capital spending; VNDirect's
statements carry them, by quarter from 2015 and by year from 2012, each quarter on its own (not year to date: four quarters add
up to the year). robots.txt of api-finfo.vndirect.com.vn answers 404, so nothing is disallowed (checked 07/11/2026); the ratios
of banks, securities firms and insurers already come from the same API.

Only the lines the table needs are kept, as decimal strings in đồng with VNDirect's signs (costs positive, cash paid out
negative). A line given twice with different values is a conflict: no value is kept and both are listed, never one chosen.
Banks and securities firms use their own layouts (LAYOUTS) and are kept apart, under data/statements-financial, with only the
lines of their scale and valuation block; insurers are skipped. The first sync of a ticker takes the
whole history; later ones take the last two years and replace those periods, keeping the older ones. A third call keeps each
year's last unadjusted close (VNDirect prices, from 2013) for the market capitalisation of that year. One JSON file per ticker
under data/statements.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from .financial_ratios import kind_of
from .leading import _get_with_retry

URL = ("https://api-finfo.vndirect.com.vn/v4/financial_statements?q=code:{symbol}~reportType:{kind}~modelType:{models}"
       "~fiscalDate:gte:{start}&size={page}")
PAGE = 60000  # rows per call: a securities firm's whole quarterly history is about 27,000; a full page may be cut and is refused
# Unadjusted daily closes (thousand đồng; from 2013), for each year's market capitalisation at that year's own price and share count.
PRICE_URL = "https://api-finfo.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{symbol}~date:gte:{start}&size=9999&fields=code,date,close"
FIRST_START, REFRESH_DAYS, MAX_AGE_DAYS, PACE_SECONDS = "2010-01-01", 730, 7, 1.0
# (model, item code) → line. Model 1 balance sheet, 2 income statement, 3 cash flow (indirect); the general layout (TT200).
LINES = {
    (2, 21000): "gross_revenue", (2, 21090): "deductions", (2, 21001): "revenue", (2, 22100): "cogs", (2, 23100): "gross_profit",
    (2, 22110): "selling", (2, 22200): "admin", (2, 21500): "fin_income", (2, 22500): "fin_expense", (2, 22510): "interest",
    (2, 23300): "associates", (2, 23200): "associates_old", (2, 23900): "other_profit", (2, 23800): "pbt", (2, 22070): "tax",
    (2, 23003): "npat", (2, 23500): "minority_profit", (2, 23000): "npat_parent",
    (1, 11100): "cash", (1, 11200): "st_investments", (1, 12700): "total_assets", (1, 13000): "liabilities", (1, 13110): "st_debt",
    (1, 13340): "lt_debt", (1, 14000): "equity", (1, 14240): "minority_equity", (1, 15000): "minority_equity_outside", (1, 14110): "charter_capital",
    (3, 22230): "depreciation", (3, 32000): "cfo", (3, 32100): "capex", (3, 33000): "cfi", (3, 34000): "cff", (3, 33600): "dividends_paid",
}
# Banks (TT49 layout: models 101 balance sheet, 102 income statement) and securities firms (TT334: 89, 90): only what their scale
# and valuation block needs. Equity includes non-controlling interests in both, as in the general layout.
_FIN_COMMON = {"charter_capital": 14110, "equity": 14000, "minority_equity": 14240, "minority_equity_outside": 15000, "total_assets": 12700}
LAYOUTS = {
    None: {"models": "1,2,3", "lines": LINES},
    "bank": {"models": "101,102,103", "lines": {**{(101, c): k for k, c in _FIN_COMMON.items()}, (102, 421701): "operating_income",
                                                 (102, 88888): "ppop", (102, 23800): "pbt", (102, 23003): "npat", (102, 23000): "npat_parent"}},
    "securities": {"models": "89,90,91", "lines": {**{(89, c): k for k, c in _FIN_COMMON.items()}, (89, 13110): "st_debt", (89, 13340): "lt_debt",
                                                   (90, 21000): "operating_revenue", (90, 23800): "pbt", (90, 23003): "npat", (90, 23000): "npat_parent"}},
}
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


def _plain(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _period(fiscal: str, kind: str) -> str:
    year, month = int(fiscal[:4]), int(fiscal[5:7])
    return str(year) if kind == "ANNUAL" else f"{year}-Q{(month + 2) // 3}"


def parse_statements(text: str, *, symbol: str, kind: str, lines: dict | None = None) -> dict:
    lines = LINES if lines is None else lines
    data = json.loads(text).get("data") or []
    if len(data) >= PAGE:
        raise ValueError("page full: the answer may be cut")
    seen: dict[tuple[str, str], set[Decimal]] = {}
    created: dict[str, str] = {}
    for r in data:
        try:
            if r.get("code") != symbol or r.get("reportType") != kind:
                continue
            line = lines.get((int(r["modelType"]), int(r["itemCode"])))
            value = Decimal(str(r["numericValue"]))
            period = _period(str(r["fiscalDate"]), kind)
        except (InvalidOperation, KeyError, TypeError, ValueError):
            continue
        if line is None or not value.is_finite():
            continue
        seen.setdefault((period, line), set()).add(value)
        day = str(r.get("createdDate") or "")[:10]
        if day and (period not in created or day < created[period]):
            created[period] = day
    periods: dict[str, dict[str, str]] = {}
    conflicts = []
    for (period, line), values in sorted(seen.items()):
        if len(values) > 1:
            conflicts.append({"period": period, "line": line, "values": [_plain(v) for v in sorted(values)]})
        else:
            periods.setdefault(period, {})[line] = _plain(next(iter(values)))
    for figures in periods.values():  # the pre-2015 layout's associates line, when the current one is absent
        old = figures.pop("associates_old", None)
        if old is not None and "associates" not in figures:
            figures["associates"] = old
    return {"periods": dict(sorted(periods.items())), "created": dict(sorted(created.items())), "conflicts": conflicts}


def parse_year_end_closes(text: str, *, symbol: str) -> dict[str, dict[str, str]]:
    """The last unadjusted close of each year with its day (the current year's latest close until the year ends)."""
    return _period_end_closes(text, symbol=symbol, period=lambda day: day[:4])


def parse_quarter_end_closes(text: str, *, symbol: str) -> dict[str, dict[str, str]]:
    """The last unadjusted close of each quarter with its day (the current quarter's latest close until it ends)."""
    return _period_end_closes(text, symbol=symbol, period=lambda day: f"{day[:4]}-Q{(int(day[5:7]) - 1) // 3 + 1}")


def _period_end_closes(text: str, *, symbol: str, period: Callable[[str], str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for r in json.loads(text).get("data") or []:
        try:
            if r.get("code") != symbol or r.get("close") is None:
                continue
            day, close = str(r["date"])[:10], Decimal(str(r["close"]))
        except (InvalidOperation, KeyError, TypeError, ValueError):
            continue
        key = period(day)
        if close.is_finite() and close > 0 and (key not in out or day > out[key]["date"]):
            out[key] = {"date": day, "close": _plain(close)}
    return dict(sorted(out.items()))


class StatementStore:
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


def _merge(old: dict | None, key: str, new: dict) -> tuple[dict, dict, list]:
    periods = {**(old or {}).get(key, {}), **new["periods"]}
    created = {**(old or {}).get(f"{key}_created", {}), **new["created"]}
    fresh = set(new["periods"]) | {c["period"] for c in new["conflicts"]}
    conflicts = [c for c in (old or {}).get(f"{key}_conflicts", []) if c["period"] not in fresh] + new["conflicts"]
    return dict(sorted(periods.items())), dict(sorted(created.items())), sorted(conflicts, key=lambda c: (c["period"], c["line"]))


def sync_statements(store: StatementStore, sectors: dict[str, str | None], *, get: Callable[[str], str], now: datetime, limit: int | None,
                    max_age_days: int = MAX_AGE_DAYS, sleep: Callable[[float], None] = time.sleep, kinds: tuple = (None,)) -> dict[str, str]:
    """Refresh the stalest watched tickers of `kinds` (None: non-financial; "bank", "securities"), never fetched first; one failing is
    reported and the others still update."""
    ages = []
    for symbol in sorted(s for s, sector in sectors.items() if kind_of(sector) in kinds):
        rec = store.read(symbol)
        fetched = datetime.fromisoformat(rec["fetched_at"]) if rec else None
        if fetched is None or (now - fetched).days >= max_age_days or "quarter_end_close" not in rec:  # synced before quarter closes were kept
            ages.append((fetched is not None, fetched or now, symbol))
    todo = [s for _, _, s in sorted(ages)]
    results = {}
    for i, symbol in enumerate(todo if limit is None else todo[:limit]):
        if i:
            sleep(PACE_SECONDS)
        old = store.read(symbol)
        start = FIRST_START if old is None else (now.date() - timedelta(days=REFRESH_DAYS)).isoformat()
        try:
            layout = LAYOUTS[kind_of(sectors[symbol])]
            parsed = {kind: parse_statements(_get_with_retry(get, URL.format(symbol=symbol, kind=kind, start=start, models=layout["models"], page=PAGE),
                                                             sleep), symbol=symbol, kind=kind, lines=layout["lines"])
                      for kind in ("QUARTER", "ANNUAL")}
            if not parsed["QUARTER"]["periods"] and not parsed["ANNUAL"]["periods"] and old is None:
                results[symbol] = "error:no_observations"
                continue
            kept = old and old.get("year_end_close") and "quarter_end_close" in old
            price_start = start if kept else FIRST_START  # synced before the closes were kept: all of them
            prices = _get_with_retry(get, PRICE_URL.format(symbol=symbol, start=price_start), sleep)
            record = {"symbol": symbol, "fetched_at": now.isoformat(), "source": "vndirect:finfo",
                      **({"kind": kind_of(sectors[symbol])} if kind_of(sectors[symbol]) else {})}
            for key, parse in (("year_end_close", parse_year_end_closes), ("quarter_end_close", parse_quarter_end_closes)):
                record[key] = dict(sorted({**(old or {}).get(key, {}), **parse(prices, symbol=symbol)}.items()))
            for kind, key in (("QUARTER", "quarters"), ("ANNUAL", "years")):
                record[key], record[f"{key}_created"], record[f"{key}_conflicts"] = _merge(old, key, parsed[kind])
            store.save(record)
            results[symbol] = "ok"
        except Exception as exc:  # one ticker never stops the others
            results[symbol] = f"error:{type(exc).__name__}"
    return results
