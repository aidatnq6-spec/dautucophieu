"""VN-Index P/E and P/B before VNDirect's own series (which starts 15/12/2017), worked out from the tickers listed on HOSE today.

The owner asked for 2013–2017 knowing the limits, written on the chart: only tickers still listed (those delisted since are missing,
so the past is biased), from 2013 (VNDirect's unadjusted prices start 02/01/2013). Data: for each HOSE ticker, one call to
VNDirect's statements filtered on the lines every layout shares (general, bank, securities, insurance: parent profit 23000, equity
14000, non-controlling interests 14240 or before 2015 15000, charter capital 14110) and one call to its unadjusted daily closes.

P/E = total market capitalisation ÷ total trailing-four-quarter parent profit; P/B = total capitalisation ÷ total parent equity, over
the tickers that on that day have a close (the latest within 30 days, as an index carries a stock between trades), four
consecutive published quarters of parent profit and a published parent equity; capitalisation = close × shares (charter capital ÷
10,000 đ of the latest published quarter). A quarter counts as out 45 days after it ends (docs/decisions/market-rules.md). A line
given twice with different values is dropped. From 2018 the same is worked out by month only, to compare with VNDirect.
"""

import calendar
import json
import os
import re
import time
from bisect import bisect_right
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from investment_agent.valuation.weekly import _latest_quarter_out

from .leading import _get_with_retry

STATEMENTS_URL = ("https://api-finfo.vndirect.com.vn/v4/financial_statements?q=code:{symbol}~reportType:QUARTER~itemCode:14000,14110,14240,15000,23000"
                  "~fiscalDate:gte:2011-01-01&size=5000")
PRICES_URL = "https://api-finfo.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{symbol}~date:gte:2013-01-01&size=9999&fields=code,date,close"
ITEMS = {14000: "equity", 14110: "capital", 14240: "minority", 15000: "minority_outside", 23000: "npat_parent"}
DAILY_BEFORE = date(2018, 1, 1)
CARRY_DAYS, PACE_SECONDS = 30, 0.5
PAR = Decimal(10000)
_Q2, _Q4 = Decimal("0.01"), Decimal("0.0001")
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


def _quarter(fiscal: str) -> str:
    return f"{fiscal[:4]}-Q{(int(fiscal[5:7]) + 2) // 3}"


def parse_quarters(text: str, *, symbol: str) -> dict[str, dict[str, Decimal]]:
    seen: dict[tuple[str, str], set] = defaultdict(set)
    for r in json.loads(text).get("data") or []:
        try:
            if r.get("code") != symbol or r.get("reportType") != "QUARTER":
                continue
            line = ITEMS.get(int(r["itemCode"]))
            value = Decimal(str(r["numericValue"]))
        except (InvalidOperation, KeyError, TypeError, ValueError):
            continue
        if line and value.is_finite():
            seen[(_quarter(str(r["fiscalDate"])), line)].add(value)
    raw: dict[str, dict[str, Decimal]] = defaultdict(dict)
    for (q, line), values in seen.items():
        if len(values) == 1:  # two different values for one line: none kept
            raw[q][line] = next(iter(values))
    out = {}
    for q, f in sorted(raw.items()):
        row = {}
        if "npat_parent" in f:
            row["npat_parent"] = f["npat_parent"]
        if "equity" in f:
            row["equity_parent"] = f["equity"] - f.get("minority", Decimal(0))  # before 2015 minorities sat outside equity
        if f.get("capital"):
            row["shares"] = f["capital"] / PAR
        if row:
            out[q] = row
    return out


def parse_closes(text: str, *, symbol: str) -> list[tuple[date, Decimal]]:
    days: dict[date, Decimal] = {}
    for r in json.loads(text).get("data") or []:
        try:
            if r.get("code") != symbol or r.get("close") is None:
                continue
            day, close = date.fromisoformat(str(r["date"])[:10]), Decimal(str(r["close"]))
        except (InvalidOperation, KeyError, TypeError, ValueError):
            continue
        if close.is_finite() and close > 0:
            days[day] = close
    month_last: dict[tuple[int, int], date] = {}
    for d in days:
        if d >= DAILY_BEFORE and d > month_last.get((d.year, d.month), date.min):
            month_last[(d.year, d.month)] = d
    keep = [d for d in days if d < DAILY_BEFORE or d == month_last[(d.year, d.month)]]
    return [(d, days[d]) for d in sorted(keep)]


class IndexHistoryStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, symbol: str) -> Path:
        if not _SYMBOL.fullmatch(symbol.upper()):
            raise ValueError("invalid symbol")
        return self.root / f"{symbol.upper()}.json"

    def read(self, symbol: str) -> dict | None:
        path = self._path(symbol)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, symbol: str, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(symbol)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


def build_history(store: IndexHistoryStore, symbols: list[str], *, get: Callable[[str], str], now: datetime,
                  sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """Fetch each ticker not stored yet (resumable); one failing is reported and the others go on."""
    results = {}
    todo = [s for s in symbols if store.read(s) is None]
    for i, symbol in enumerate(todo):
        if i:
            sleep(PACE_SECONDS)
        try:
            quarters = parse_quarters(_get_with_retry(get, STATEMENTS_URL.format(symbol=symbol), sleep), symbol=symbol)
            closes = parse_closes(_get_with_retry(get, PRICES_URL.format(symbol=symbol), sleep), symbol=symbol)
            store.save(symbol, {"symbol": symbol, "fetched_at": now.isoformat(), "source": "vndirect:finfo",
                                "quarters": {q: {k: format(v.normalize(), "f") for k, v in f.items()} for q, f in quarters.items()},
                                "closes": [[d.isoformat(), format(c.normalize(), "f")] for d, c in closes]})
            results[symbol] = "ok"
        except Exception as exc:  # one ticker never stops the others
            results[symbol] = f"error:{type(exc).__name__}"
    return results


def _previous(q: str) -> str:
    y, n = int(q[:4]), int(q[-1])
    return f"{y}-Q{n - 1}" if n > 1 else f"{y - 1}-Q4"


def _figures(quarters: dict[str, dict], latest: str) -> tuple[Decimal, Decimal, Decimal] | None:
    """(trailing four quarters' parent profit, parent equity, shares) to the quarter that should be out, or None when it is missing:
    a ticker whose latest quarters are absent is left out, never valued on older figures."""
    if latest not in quarters:
        return None
    window = [latest]
    for _ in range(3):
        window.append(_previous(window[-1]))
    profits = [quarters.get(q, {}).get("npat_parent") for q in window]
    f = quarters[latest]
    if any(p is None for p in profits) or f.get("equity_parent") is None or not f.get("shares"):
        return None
    return sum(profits, Decimal(0)), f["equity_parent"], f["shares"]


def _month_end(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def _load(rec: dict) -> tuple[dict, list]:
    quarters = {q: {k: Decimal(v) for k, v in f.items()} for q, f in rec.get("quarters", {}).items()}
    closes = [(date.fromisoformat(d), Decimal(c)) for d, c in rec.get("closes", [])]
    return quarters, closes


def _close_on(closes: list, day: date) -> Decimal | None:
    days = [d for d, _ in closes]
    i = bisect_right(days, day) - 1
    return closes[i][1] if i >= 0 and (day - days[i]).days <= CARRY_DAYS else None


def top_members(records: dict[str, dict], *, size: int = 30) -> Callable[[str, date], bool]:
    """An estimated VN30-like basket: the `size` largest by capitalisation on the last day of December (holding from 1 February) and
    of June (from 1 August); before the first change, the largest on the first day with prices. Free float and liquidity, which the
    real rules also weigh, are not known here."""
    loaded = {s: _load(r) for s, r in records.items()}
    first = min((c[0][0] for _, c in loaded.values() if c), default=None)
    if first is None:
        return lambda symbol, day: False
    reviews = [(first, first)]
    for year in range(first.year - 1, max(c[-1][0].year for _, c in loaded.values() if c) + 1):
        reviews += [(date(year, 12, 31), date(year + 1, 2, 1)), (date(year, 6, 30), date(year, 8, 1))]
    baskets = []
    for seen, start in sorted(reviews, key=lambda r: r[1]):
        if seen < first:
            continue
        caps = []
        for symbol, (quarters, closes) in loaded.items():
            close, f = _close_on(closes, seen), quarters.get(_latest_quarter_out(seen), {})
            if close is not None and f.get("shares"):
                caps.append((close * f["shares"], symbol))
        baskets.append((start, {s for _, s in sorted(caps, reverse=True)[:size]}))
    starts = [b[0] for b in baskets]

    def member(symbol: str, day: date) -> bool:
        i = bisect_right(starts, day) - 1
        return i >= 0 and symbol in baskets[i][1]
    return member


def compute_index(records: dict[str, dict], *, before: date | None = None, members: Callable[[str, date], bool] | None = None) -> dict[date, dict]:
    """Daily values before 2018 (each ticker's latest close within 30 days), then one value per month (key: the month's last day);
    `members` limits each day to a basket."""
    tickers = []
    for symbol, rec in records.items():
        quarters = {q: {k: Decimal(v) for k, v in f.items()} for q, f in rec.get("quarters", {}).items()}
        closes = [(date.fromisoformat(d), Decimal(c)) for d, c in rec.get("closes", [])]
        if quarters and closes:
            tickers.append((symbol, quarters, closes))
    daily_days = sorted({d for _, _, closes in tickers for d, _ in closes if d < DAILY_BEFORE and (before is None or d < before)})
    months = sorted({_month_end(d) for _, _, closes in tickers for d, _ in closes if d >= DAILY_BEFORE})
    sums: dict[date, list] = defaultdict(lambda: [Decimal(0), Decimal(0), Decimal(0), 0])
    inside = members or (lambda symbol, day: True)
    for symbol, quarters, closes in tickers:
        days = [d for d, _ in closes]
        cache: dict[str, object] = {}
        for day in daily_days:
            i = bisect_right(days, day) - 1
            if i < 0 or (day - days[i]).days > CARRY_DAYS or days[i] >= DAILY_BEFORE or not inside(symbol, day):
                continue
            _add(sums[day], closes[i][1], quarters, day, cache)
        for d, close in closes:
            if d >= DAILY_BEFORE and inside(symbol, _month_end(d)):
                _add(sums[_month_end(d)], close, quarters, _month_end(d), cache)
    out = {}
    for day in daily_days + months:
        cap, profit, equity, n = sums.get(day, [0, 0, 0, 0])
        if n and profit > 0 and equity > 0:
            out[day] = {"pe": (cap / profit).quantize(_Q2, ROUND_HALF_UP), "pb": (cap / equity).quantize(_Q2, ROUND_HALF_UP), "tickers": n}
    return out


def _add(acc: list, close: Decimal, quarters: dict, day: date, cache: dict) -> None:
    key = _latest_quarter_out(day)  # the quarter due by then (45 days after it ends), whatever the ticker has
    if key not in cache:
        cache[key] = _figures(quarters, key)
    figures = cache[key]
    if figures is None:
        return
    profit, equity, shares = figures
    acc[0] += close * 1000 * shares
    acc[1] += profit
    acc[2] += equity
    acc[3] += 1


def compare(calc: dict[date, dict], vndirect: dict[str, list]) -> dict:
    """The worked-out values against VNDirect's, month by month (each side's last value of the month)."""
    out = {}
    for k in ("pe", "pb"):
        mine = {}
        for d in sorted(calc):
            mine[d.strftime("%Y-%m")] = calc[d][k]
        theirs = {}
        for t, v in vndirect.get(k, []):
            theirs[t.strftime("%Y-%m")] = Decimal(str(v))
        both = sorted(set(mine) & set(theirs))
        gaps = [abs(mine[m] / theirs[m] - 1) for m in both if theirs[m] > 0]
        out[k] = {"months": len(gaps), "mean_abs": str((sum(gaps) / len(gaps)).quantize(_Q4, ROUND_HALF_UP)) if gaps else None,
                  "max_abs": str(max(gaps).quantize(_Q4, ROUND_HALF_UP)) if gaps else None, "from": both[0] if both else None,
                  "to": both[-1] if both else None}
    return out
