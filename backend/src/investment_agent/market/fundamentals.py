"""Statement figures, cash dividends and share issues per ticker (Vnstock free tier) for the reference valuation.

Only what the valuation needs is kept: parent-company profit after tax, basic EPS and equity, by year and by
quarter; cash dividends per share and share-issue ratios from company events (ex-right dates). Amounts are
decimal strings in đồng, one JSON file per ticker under data/fundamentals.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

NPAT, EPS, EQUITY = "IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY", "IS_BASIC_EARNINGS_PER_SHARE", "BS_EQUITY"
NET_PROFIT = "IS_NET_PROFIT_AFTER_TAX"  # securities firms report only this line, and no EPS
# Annual lines for Chất lượng báo cáo (F-Score and the warning signs); the free tier's cash flow statement has totals only.
ANNUAL = {"IS_NET_REVENUE": "revenue", "IS_GROSS_PROFIT": "gross_profit", "IS_SELLING_EXPENSES": "selling",
          "IS_GENERAL_AND_ADMINISTRATIVE_EXPENSES": "admin", NET_PROFIT: "profit", "BS_TOTAL_ASSETS": "total_assets",
          "BS_SHORT_TERM_ASSETS": "current_assets", "BS_SHORT_TERM_LIABILITIES": "current_liabilities",
          "BS_LONG_TERM_LIABILITIES": "long_liabilities", "BS_SHORT_TERM_RECEIVABLES": "receivables",
          "CF_NET_CASH_FLOWS_FROM_OPERATING_ACTIVITIES": "cfo"}
# Share issues by kind, from the event titles: bonus shares and stock dividends raise no money; rights, placements and ESOP do.
_ISSUE_KINDS = (("bonus", re.compile(r"cổ phiếu thưởng|cổ tức bằng cổ phiếu", re.I)),
                ("raise", re.compile(r"quyền mua|riêng lẻ|chào bán|CBCNV|ESOP|người lao động", re.I)))
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
    for figures in out.values():  # parent-company profit when reported, otherwise net profit
        net = figures.pop("net_profit", None)
        if "npat" not in figures and net is not None and "npat" in names.values():
            figures["npat"] = net
    return dict(sorted(out.items()))


def _day(value) -> str | None:
    if value is None or str(value) in ("NaT", "nan", "None", ""):
        return None
    return value.date().isoformat() if hasattr(value, "date") else str(value)[:10]


def _events(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    dividends, issues, kinds = [], [], []
    for r in rows:
        day, title = _day(r.get("exright_date")), str(r.get("event_title_vi") or "")
        if day is None:
            continue
        if r.get("event_code") == "DIV" and (m := _CASH.search(title)):
            dividends.append({"date": day, "cash": _num(m.group(1).replace(",", "").replace(".", ""))})
        elif r.get("event_code") == "ISS":
            if m := _RATIO.search(title):
                issues.append({"date": day, "ratio": _num(Decimal(m.group(1).replace(",", ".")) / 100)})
            kinds.append({"date": day, "kind": next((k for k, p in _ISSUE_KINDS if p.search(title)), "other")})
    return (sorted(dividends, key=lambda d: d["date"]), sorted(issues, key=lambda d: d["date"]),
            sorted(kinds, key=lambda d: (d["date"], d["kind"])))


def build_record(symbol: str, frames: dict, fetched_at: datetime) -> dict:
    dividends, issues, share_issues = _events(frames["events"])
    overview = (frames.get("overview") or [{}])[0]
    return {"symbol": symbol.upper(), "fetched_at": fetched_at.isoformat(), "source": "vnstock:vci",
            "years": _by_period(frames["income_year"] + frames["balance_year"], {NPAT: "npat", NET_PROFIT: "net_profit", EPS: "eps", EQUITY: "equity"}),
            "quarters": _by_period(frames["income_quarter"] + frames["balance_quarter"], {NPAT: "npat", NET_PROFIT: "net_profit", EQUITY: "equity"}),
            "annual": _by_period(frames["income_year"] + frames["balance_year"] + frames.get("cash_year", []), ANNUAL),
            "dividends": dividends, "issues": issues, "share_issues": share_issues,
            # Listed shares from the company overview: the share count when no EPS is reported (securities firms).
            "shares_outstanding": _num(overview.get("outstanding_shares"))}


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


PACE_SECONDS, RETRY_WAIT_SECONDS = 15, 65


def _with_retry(call, sleep):
    try:
        return call()
    except Exception:
        sleep(RETRY_WAIT_SECONDS)  # usually the 60-calls-per-minute limit
        return call()


def latest_quarter(record: dict) -> str | None:
    with_profit = [q for q, f in record.get("quarters", {}).items() if f.get("npat") is not None]
    return max(with_profit) if with_profit else None


def _quarter_seen(record: dict, previous: dict | None, today) -> dict | None:
    """The latest quarter with profit and the day it first appeared here (kept while the quarter stays the same)."""
    quarter = latest_quarter(record)
    if quarter is None:
        return None
    seen = (previous or {}).get("latest_quarter_seen")
    return seen if seen and seen.get("quarter") == quarter else {"quarter": quarter, "on": today.isoformat()}


def sync_fundamentals(store: "FundamentalsStore", series, symbols: list[str], *, provider, now, limit: int | None,
                      max_age_days: int = 7, sleep=time.sleep) -> dict:
    """Refresh statements (and 8 years of daily closes for year-end prices) for the stalest tickers, paced for the rate limit."""
    todo = store.stale(symbols, now=now, max_age_days=max_age_days)
    todo = todo if limit is None else todo[:limit]
    updated, errors, today = [], {}, now.date()
    for i, sym in enumerate(todo):
        if i:
            sleep(PACE_SECONDS)
        try:
            frames = _with_retry(lambda: provider.fundamentals_frames(sym), sleep)
            key = f"{sym}-1d"
            start = today - timedelta(days=2920 if len(series.read(key)) < 400 else 60)
            series.upsert(key, _with_retry(lambda: provider.fetch_closes(sym, start, today, interval="1D", index=False), sleep))
            record, previous = build_record(sym, frames, now), store.read(sym)
            record["latest_quarter_seen"] = _quarter_seen(record, previous, today)
            store.save(record)
            updated.append(sym)
        except Exception as exc:  # one ticker never stops the others
            errors[sym] = f"error:{type(exc).__name__}"
    return {"updated": updated, "errors": errors}
