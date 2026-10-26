# Định giá tham khảo (reference valuation for 50 tickers) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Spec:** `docs/superpowers/specs/2026-10-26-dinh-gia-tham-khao-design.md` (owner-approved 2026-10-26). The spec is the authority.

**Goal:** A **Định giá** page that values each of the 50 watched tickers with sector-appropriate methods, from free Vnstock statements, and says whether the current price is **Rẻ / Hợp lý / Đắt** against a fair-value range.

**Architecture:**
- **Statements:** a throttled sync stores annual and quarterly statement figures, cash dividends and share issues per ticker under `data/fundamentals/<sym>.json`. The same sync tops up 8 years of daily closes in `data/trend-sources/<sym>-1d.json`, the series store from the Xu hướng work.
- **Valuation:** pure functions in `valuation/reference.py` derive shares, TTM EPS, BVPS, ROE, and historical P/E and P/B, then compute seven methods, pick them by ICB sector, and apply the owner's threshold.
- **Delivery:** `GET /internal/fairvalue` computes on request from stored data, the latest close and the owner's valuation settings (Firestore `settings/valuation`). A Next page renders the result.

**Tech Stack:** Python 3.11 / FastAPI / pydantic, Decimal for money; Next.js client components; pytest; Playwright.

## Global constraints

- **Money:** values in đồng are `Decimal` and serialized as strings. Values are rounded to whole đồng (half up) and ratios to 4 places.
- **Price units:** Vnstock closes stored in `data/trend-sources` are in **thousand đồng**; multiply by 1,000 before any P/E or P/B math. `market.price()` (PriceStore) is already in đồng.
- **No fabrication:** a method without enough data returns `value: None` with a Vietnamese `reason`. A ticker with fewer than 2 valid methods gets verdict `insufficient`.
- **Not a recommendation:** nothing here touches the recommendation gates, buy zones or the universe.
- **Rate limit:** Vnstock Community allows 60 calls per minute, and a statement call uses several internally. Pace calls, and on any fetch error wait 65 s and retry once.
- **Process:** TDD, watching each test fail first. Run the full backend suite before each commit and `scripts\windows\verify.ps1` before the PR. Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Where to work:** the worktree `D:\GitHub\dautucophieu\.worktrees\investment-agent`, on a new branch from `docs/valuation-design`. Python is `./.venv/Scripts/python.exe`. The worktree venv has no `vnstock`, so live checks use `/d/GitHub/dautucophieu/.venv/Scripts/python.exe` with `PYTHONPATH=backend/src`.

## Real data shapes (checked 2026-10-26)

- **Statements:** `Fundamental().equity(sym).income_statement/balance_sheet(period="year"|"quarter", format="long")` returns rows `{period, id, name, value, ...}`:
  - year periods are `"2018"`…`"2025"`;
  - quarter periods are `"2024-Q3"`…`"2026-Q2"`;
  - the ids used are `IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY`, `IS_BASIC_EARNINGS_PER_SHARE` and `BS_EQUITY`.
- **Events:** `Company(source="VCI", symbol=sym).events()` returns rows with `event_code`, `event_title_vi` and `exright_date` (a pandas Timestamp or NaT):
  - cash dividend: `event_code == "DIV"`, title `"Trả cổ tức bằng tiền mặt - Đợt 1 2025 - 1,000 VND"`;
  - share issue: `event_code == "ISS"`, title `"Phát hành cổ phiếu - Cổ phiếu thưởng tỉ lệ 10.0%"` (also ESOP and rights issues, as "tỉ lệ x%").

## Interfaces

| Producer | Consumer | Contract |
|---|---|---|
| T1 `market/fundamentals.py` | T2, T3, T5 | `build_record(symbol, frames, fetched_at) -> dict`, with `frames` = `{"income_year","balance_year","income_quarter","balance_quarter","events"}` lists of row dicts. `FundamentalsStore(root).read(sym) / save(record) / stale(symbols, now, max_age_days) -> list[str]` |
| T2 `valuation/reference.py` | T5 | `metrics(record, *, today, year_end_prices) -> dict \| None`, `year_end_prices(points, *, today) -> dict[int, Decimal]`, `value_ticker(...) -> row dict`, `reference_board(...) -> dict` |
| T3 sync | T4 | `sync_fundamentals(...) -> {"updated": [...], "errors": {...}}` |
| T4 settings | T5, T6 | `ValuationSettings(required_return, long_term_growth, threshold)`, `valuation_settings(repo, owner) -> (ValuationSettings, version)` |

---

### Task 1: Statement record and store

**Files:**
- Create: `backend/src/investment_agent/market/fundamentals.py`
- Test: `backend/tests/market/test_fundamentals.py`

**Step 1: Failing tests**

```python
from datetime import datetime, timezone

import pandas as pd

from investment_agent.market.fundamentals import FundamentalsStore, build_record

NOW = datetime(2026, 10, 26, 13, tzinfo=timezone.utc)
NPAT, EPS, EQ = "IS_PROFIT_AFTER_TAX_FOR_SHAREHOLDERS_OF_PARENT_COMPANY", "IS_BASIC_EARNINGS_PER_SHARE", "BS_EQUITY"


def rows(period, **ids):
    return [{"period": period, "id": k, "name": "x", "value": v} for k, v in ids.items()]


FRAMES = {
    "income_year": rows("2024", **{NPAT: 1.5e9, EPS: 1500.0}) + rows("2025", **{NPAT: 2.0e9, EPS: 2000.0, "IS_NET_REVENUE": 9e9}),
    "balance_year": rows("2024", **{EQ: 13e9}) + rows("2025", **{EQ: 15e9}),
    "income_quarter": rows("2026-Q1", **{NPAT: 5.5e8}) + rows("2026-Q2", **{NPAT: float("nan")}),
    "balance_quarter": rows("2026-Q2", **{EQ: 16e9}),
    "events": [
        {"event_code": "DIV", "event_title_vi": "Trả cổ tức bằng tiền mặt - Đợt 1 2025 - 1,000 VND", "exright_date": pd.Timestamp("2025-12-01", tz="Asia/Ho_Chi_Minh")},
        {"event_code": "DIV", "event_title_vi": "Trả cổ tức bằng tiền mặt - Đợt 2 2025 - 1,500 VND", "exright_date": pd.NaT},
        {"event_code": "ISS", "event_title_vi": "Phát hành cổ phiếu - Cổ phiếu thưởng tỉ lệ 10.0%", "exright_date": pd.Timestamp("2026-09-21", tz="Asia/Ho_Chi_Minh")},
        {"event_code": "AGME", "event_title_vi": "Đại hội cổ đông", "exright_date": pd.Timestamp("2026-04-01", tz="Asia/Ho_Chi_Minh")},
    ],
}


def test_record_keeps_only_the_needed_lines_and_parses_events():
    r = build_record("fpt", FRAMES, NOW)
    assert r["symbol"] == "FPT" and r["fetched_at"] == NOW.isoformat() and r["source"] == "vnstock:vci"
    assert r["years"] == {"2024": {"npat": "1500000000", "eps": "1500", "equity": "13000000000"},
                          "2025": {"npat": "2000000000", "eps": "2000", "equity": "15000000000"}}
    assert r["quarters"] == {"2026-Q1": {"npat": "550000000"}, "2026-Q2": {"equity": "16000000000"}}  # NaN dropped
    assert r["dividends"] == [{"date": "2025-12-01", "cash": "1000"}]  # undated event skipped
    assert r["issues"] == [{"date": "2026-09-21", "ratio": "0.1"}]


def test_store_round_trips_and_lists_stale_tickers_oldest_first(tmp_path):
    s = FundamentalsStore(tmp_path / "fundamentals")
    s.save(build_record("FPT", FRAMES, datetime(2026, 10, 10, tzinfo=timezone.utc)))
    s.save(build_record("MBB", FRAMES, datetime(2026, 10, 25, tzinfo=timezone.utc)))
    assert s.read("FPT")["years"]["2025"]["eps"] == "2000" and s.read("VCB") is None
    assert s.stale(["MBB", "FPT", "VCB"], now=NOW, max_age_days=7) == ["VCB", "FPT"]  # missing first, then oldest
```

**Step 2:** Run `./.venv/Scripts/python.exe -m pytest backend/tests/market/test_fundamentals.py -q -p no:warnings`. Expected: collection error (module missing).

**Step 3: Implement**

```python
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
```

**Step 4:** Run the tests; expect 2 passed. Then run the full suite.

**Step 5:** Commit `feat: statement record and store for the reference valuation`.

---

### Task 2: Reference valuation (metrics, methods, sectors, verdict)

**Files:**
- Create: `backend/src/investment_agent/valuation/reference.py`
- Test: `backend/tests/valuation/test_reference.py` (create the folder if missing, with the same `__init__` convention as the other test folders)

**Step 1: Failing tests.** Hand-computed fixture: 1,000,000 shares. Year-end prices (đồng) and the resulting P/E and P/B:

| Year | Price | P/E | P/B |
|---|---|---|---|
| 2021 | 15,000 | 15 | 1.5 |
| 2022 | 14,400 | 12 | 1.309 |
| 2023 | 10,000 | 10 | 0.833 |
| 2024 | 21,000 | 14 | 1.615 |
| 2025 | 26,000 | 13 | 1.733 |

Medians: P/E 13, P/B 1.5. TTM profit is 4 × 550m = 2.2bn, so EPS TTM = 2,200 and BVPS = 16bn / 1m = 16,000. ROE = 2.2 / ((16 + 14) / 2) = 0.146667.

```python
from datetime import date, datetime
from decimal import Decimal

from investment_agent.valuation.reference import (
    Settings, metrics, methods_for, reference_board, value_ticker, year_end_prices,
)

TODAY = date(2026, 10, 26)
PRICES = {2021: Decimal(15000), 2022: Decimal(14400), 2023: Decimal(10000), 2024: Decimal(21000), 2025: Decimal(26000)}


def record(issues=()):
    years = {"2021": ("1000000000", "1000", "10000000000"), "2022": ("1200000000", "1200", "11000000000"),
             "2023": ("1000000000", "1000", "12000000000"), "2024": ("1500000000", "1500", "13000000000"),
             "2025": ("2000000000", "2000", "15000000000")}
    quarters = {q: {"npat": "550000000"} for q in ("2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2")}
    quarters["2025-Q2"] = {"npat": "500000000", "equity": "14000000000"}
    quarters["2026-Q2"]["equity"] = "16000000000"
    divs = [{"date": f"{y}-07-01", "cash": "1000"} for y in (2021, 2022, 2023, 2024)] + [
        {"date": "2025-12-01", "cash": "1000"}, {"date": "2026-05-28", "cash": "1000"}]
    return {"symbol": "AAA", "fetched_at": "2026-10-26T00:00:00+00:00", "source": "t",
            "years": {y: {"npat": n, "eps": e, "equity": q} for y, (n, e, q) in years.items()},
            "quarters": dict(sorted(quarters.items())), "dividends": divs, "issues": list(issues)}


def test_metrics_derive_shares_ttm_eps_bvps_roe_and_history():
    m = metrics(record(), today=TODAY, year_end_prices=PRICES)
    assert (m["shares"], m["eps_ttm"], m["bvps"]) == (Decimal(1000000), Decimal(2200), Decimal(16000))
    assert m["roe"].quantize(Decimal("0.0001")) == Decimal("0.1467")
    assert m["pe_history"] == {2021: 15, 2022: 12, 2023: 10, 2024: 14, 2025: 13}
    assert m["pb_history"][2021] == Decimal("1.5") and m["dividend_ttm"] == Decimal(2000) and m["paying_years"] == 5
    assert m["latest_year"] == "2025" and m["latest_quarter"] == "2026-Q2"


def test_share_issues_after_the_annual_report_raise_the_share_count():
    m = metrics(record([{"date": "2026-09-21", "ratio": "0.1"}, {"date": "2025-07-01", "ratio": "0.5"}]), today=TODAY, year_end_prices=PRICES)
    assert m["shares"] == Decimal(1100000)  # only the 2026 issue is after FY2025


def test_each_method_on_the_hand_computed_case():
    m = metrics(record(), today=TODAY, year_end_prices=PRICES)
    peers = {"pe": [Decimal(10), Decimal(12), Decimal(14)], "pb": [Decimal(1), Decimal(2), Decimal(3)]}
    got = {x["method"]: x["value"] for x in methods_for(["pe_history", "pb_history", "pe_peers", "pb_peers", "justified_pb", "ddm", "pe_normalized"],
                                                        m, peers, Settings())}
    assert got == {"pe_history": Decimal(28600), "pb_history": Decimal(24000), "pe_peers": Decimal(26400), "pb_peers": Decimal(32000),
                   "justified_pb": Decimal(19333), "ddm": Decimal(26250), "pe_normalized": Decimal(17420)}


def test_methods_explain_why_they_do_not_apply():
    m = metrics(record(), today=TODAY, year_end_prices={2025: Decimal(26000)})
    out = {x["method"]: x for x in methods_for(["pe_history", "pe_peers", "justified_pb"], m, {"pe": [Decimal(10)], "pb": []},
                                               Settings(required_return=Decimal("0.13"), long_term_growth=Decimal("0.20")))}
    assert out["pe_history"]["value"] is None and "4 năm" in out["pe_history"]["reason"]
    assert out["pe_peers"]["value"] is None and "3 mã" in out["pe_peers"]["reason"]
    assert out["justified_pb"]["value"] is None


def test_verdict_uses_the_median_of_sector_methods_and_the_threshold():
    m = metrics(record(), today=TODAY, year_end_prices=PRICES)
    peers = {"pe": [Decimal(10), Decimal(12), Decimal(14)], "pb": [Decimal(1), Decimal(2), Decimal(3)]}
    tech = lambda price: value_ticker("AAA", "Công nghệ Thông tin", m, price, peers, Settings())  # noqa: E731
    assert tech(Decimal(20000))["fair"] == "26400" and tech(Decimal(20000))["verdict"] == "cheap"
    assert tech(Decimal(30000))["verdict"] == "fair" and tech(Decimal(32000))["verdict"] == "expensive"
    bank = value_ticker("AAA", "Ngân hàng", m, Decimal(26300), peers, Settings())
    assert (bank["fair"], bank["low"], bank["high"], bank["verdict"]) == ("26300", "19333", "32000", "fair")
    lonely = value_ticker("AAA", "Bất động sản", metrics(record(), today=TODAY, year_end_prices={}), Decimal(1), peers, Settings())
    assert lonely["verdict"] == "insufficient" and lonely["fair"] is None
    assert value_ticker("AAA", "Ngân hàng", m, None, peers, Settings())["verdict"] == "insufficient"


def test_year_end_prices_take_the_last_close_of_each_finished_year_in_dong():
    pts = [(datetime(2024, 12, 30), 20.5), (datetime(2024, 12, 31), 21.0), (datetime(2025, 12, 31), 26.0), (datetime(2026, 10, 23), 57.0)]
    assert year_end_prices(pts, today=TODAY) == {2024: Decimal("21000"), 2025: Decimal("26000")}


def test_board_values_every_symbol_with_peers_from_the_same_sector():
    recs = {s: record() for s in ("AAA", "BBB", "CCC", "DDD")}
    board = reference_board(["AAA", "BBB", "CCC", "DDD", "EEE"], sectors={s: "Ngân hàng" for s in recs},
                            records=recs, prices={s: Decimal(26000) for s in recs}, year_end={s: PRICES for s in recs},
                            settings=Settings(), today=TODAY, held={"AAA"})
    rows = {r["symbol"]: r for r in board["rows"]}
    assert rows["AAA"]["held"] is True and rows["AAA"]["verdict"] in {"cheap", "fair", "expensive"}
    assert rows["EEE"]["verdict"] == "insufficient" and rows["EEE"]["sector"] == "Chưa phân ngành"
    assert board["settings"] == {"required_return": "0.13", "long_term_growth": "0.05", "threshold": "0.2"}
```

Arithmetic for the expected values:
- `justified_pb` = 16,000 × (0.146667 − 0.05) / 0.08 = 16,000 × 1.208333 = 19,333.
- `ddm` = 2,000 × 1.05 / 0.08 = 26,250.
- `pe_normalized` = (6.7bn / 5 / 1m) × 13 = 1,340 × 13 = 17,420.
- Technology median of the methods is 26,400 (28,600, 26,400 and 26,250).
- Bank median of 4 methods = (24,000 + 28,600) / 2 = 26,300; low 19,333, high 32,000.
- At price 20,000 the gap is −24.2%, so cheap. At 30,000 it is +13.6%, so fair. At 32,000 it is +21.2%, so expensive.

**Step 2:** Run `./.venv/Scripts/python.exe -m pytest backend/tests/valuation/test_reference.py -q -p no:warnings`. Expected: collection error.

**Step 3: Implement** `valuation/reference.py`:

```python
"""Reference valuation: several sector-appropriate methods per ticker from free statement data, for the owner's
"rẻ hay đắt" question. Not a recommendation and not wired to buy zones or the universe.

Historical P/E and P/B use the adjusted year-end close × today's share count over that year's profit or equity,
so bonus issues and splits do not distort them. Shares = latest annual parent profit / basic EPS, times share
issues after that year. A method without enough data returns no value and a reason; fewer than two values
means no verdict.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

UNCLASSIFIED = "Chưa phân ngành"
SECTOR_METHODS = {
    "Ngân hàng": ("pb_history", "justified_pb", "pe_history", "pb_peers"),
    "Dịch vụ tài chính": ("pb_history", "pe_history", "pb_peers"),
    "Bảo hiểm": ("pb_history", "pe_history", "pb_peers"),
    "Bất động sản": ("pb_history", "pe_history"),
    "Tài nguyên Cơ bản": ("pe_normalized", "pb_history"),
    "Hóa chất": ("pe_normalized", "pb_history"),
    "Dầu khí": ("pe_normalized", "pb_history"),
}
DEFAULT_METHODS = ("pe_history", "pe_peers", "ddm")
LABELS = {"pe_history": "P/E lịch sử", "pb_history": "P/B lịch sử", "pe_peers": "P/E cùng ngành", "pb_peers": "P/B cùng ngành",
          "justified_pb": "P/B hợp lý theo ROE", "ddm": "Chiết khấu cổ tức", "pe_normalized": "P/E trên lợi nhuận bình quân"}
MIN_YEARS, MIN_PEERS, MIN_PAYING_YEARS = 4, 3, 4


@dataclass(frozen=True)
class Settings:
    required_return: Decimal = Decimal("0.13")
    long_term_growth: Decimal = Decimal("0.05")
    threshold: Decimal = Decimal("0.20")


def _vnd(x: Decimal) -> Decimal:
    return x.quantize(Decimal(1), ROUND_HALF_UP)


def _median(values: list[Decimal]) -> Decimal:
    v = sorted(values)
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def _d(value) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def year_end_prices(points, *, today: date) -> dict[int, Decimal]:
    """Last stored close of each finished calendar year, converted from thousand đồng (Vnstock) to đồng."""
    out: dict[int, Decimal] = {}
    for t, close in points:
        if t.year < today.year:
            out[t.year] = Decimal(str(close)) * 1000
    return out


def metrics(record: dict, *, today: date, year_end_prices: dict[int, Decimal]) -> dict | None:
    years = record["years"]
    annual = [y for y in sorted(years) if _d(years[y].get("npat")) and _d(years[y].get("eps"))]
    if not annual:
        return None
    latest_year = annual[-1]
    shares = _d(years[latest_year]["npat"]) / _d(years[latest_year]["eps"])
    for issue in record.get("issues", []):
        if f"{latest_year}-12-31" < issue["date"] <= today.isoformat():
            shares *= 1 + Decimal(issue["ratio"])
    shares = shares.quantize(Decimal(1), ROUND_HALF_UP)
    quarters = record["quarters"]
    with_profit = [q for q in sorted(quarters) if _d(quarters[q].get("npat")) is not None]
    with_equity = [q for q in sorted(quarters) if _d(quarters[q].get("equity")) is not None]
    npat_ttm = sum(_d(quarters[q]["npat"]) for q in with_profit[-4:]) if len(with_profit) >= 4 else None
    latest_quarter = with_equity[-1] if with_equity else None
    equity_now = _d(quarters[latest_quarter]["equity"]) if latest_quarter else None
    prev_key = f"{int(latest_quarter[:4]) - 1}{latest_quarter[4:]}" if latest_quarter else None
    equity_prev = _d(quarters.get(prev_key, {}).get("equity")) if prev_key else None
    pe_history, pb_history = {}, {}
    for y in sorted(years):
        price, npat, eq = year_end_prices.get(int(y)), _d(years[y].get("npat")), _d(years[y].get("equity"))
        if price is None:
            continue
        if npat and npat > 0:
            pe_history[int(y)] = price * shares / npat
        if eq and eq > 0:
            pb_history[int(y)] = price * shares / eq
    npats = [_d(years[y]["npat"]) for y in sorted(years) if _d(years[y].get("npat")) is not None]
    year_ago = (today - timedelta(days=365)).isoformat()
    divs = record.get("dividends", [])
    paying = {int(d["date"][:4]) for d in divs if today.year - 5 <= int(d["date"][:4]) <= today.year - 1}
    return {"shares": shares, "eps_ttm": npat_ttm / shares if npat_ttm is not None else None,
            "bvps": equity_now / shares if equity_now is not None else None,
            "roe": npat_ttm / ((equity_now + equity_prev) / 2) if None not in (npat_ttm, equity_now, equity_prev) else None,
            "pe_history": pe_history, "pb_history": pb_history,
            "eps_normalized": (sum(npats) / len(npats)) / shares if npats else None,
            "dividend_ttm": sum((Decimal(d["cash"]) for d in divs if year_ago < d["date"] <= today.isoformat()), Decimal(0)),
            "paying_years": len(paying), "latest_year": latest_year, "latest_quarter": latest_quarter}


def _result(method, value=None, reason=None, **inputs):
    clean = {k: (str(v.quantize(Decimal("0.0001"), ROUND_HALF_UP)) if isinstance(v, Decimal) else v) for k, v in inputs.items()}
    return {"method": method, "label": LABELS[method], "value": _vnd(value) if value is not None else None, "reason": reason, "inputs": clean}


def _method(name: str, m: dict, peers: dict, s: Settings) -> dict:
    eps, bvps, r, g = m["eps_ttm"], m["bvps"], s.required_return, s.long_term_growth
    if name in ("pe_history", "pe_normalized"):
        base = eps if name == "pe_history" else m["eps_normalized"]
        if len(m["pe_history"]) < MIN_YEARS:
            return _result(name, reason=f"Cần P/E của ít nhất {MIN_YEARS} năm có lãi và có giá cuối năm")
        if not base or base <= 0:
            return _result(name, reason="Lợi nhuận không dương")
        pe = _median(list(m["pe_history"].values()))
        return _result(name, base * pe, eps=base, pe_median=pe, years=len(m["pe_history"]))
    if name == "pb_history":
        if len(m["pb_history"]) < MIN_YEARS:
            return _result(name, reason=f"Cần P/B của ít nhất {MIN_YEARS} năm có giá cuối năm")
        if not bvps or bvps <= 0:
            return _result(name, reason="Vốn chủ sở hữu không dương")
        pb = _median(list(m["pb_history"].values()))
        return _result(name, bvps * pb, bvps=bvps, pb_median=pb, years=len(m["pb_history"]))
    if name in ("pe_peers", "pb_peers"):
        base, ratios = (eps, peers.get("pe", [])) if name == "pe_peers" else (bvps, peers.get("pb", []))
        if len(ratios) < MIN_PEERS:
            return _result(name, reason=f"Cần ít nhất {MIN_PEERS} mã cùng ngành có số liệu")
        if not base or base <= 0:
            return _result(name, reason="Lợi nhuận hoặc vốn chủ sở hữu không dương")
        med = _median(ratios)
        return _result(name, base * med, base=base, peer_median=med, peers=len(ratios))
    if name == "justified_pb":
        roe = m["roe"]
        if roe is None or not bvps or bvps <= 0:
            return _result(name, reason="Thiếu ROE hoặc vốn chủ sở hữu")
        if roe <= g or r <= g:
            return _result(name, reason="ROE không cao hơn tăng trưởng dài hạn")
        pb = (roe - g) / (r - g)
        return _result(name, bvps * pb, bvps=bvps, roe=roe, justified_pb=pb)
    if name == "ddm":
        d = m["dividend_ttm"]
        if m["paying_years"] < MIN_PAYING_YEARS or not d:
            return _result(name, reason=f"Cần trả cổ tức tiền mặt ít nhất {MIN_PAYING_YEARS} trong 5 năm gần nhất")
        if r <= g:
            return _result(name, reason="Lợi suất yêu cầu phải lớn hơn tăng trưởng")
        return _result(name, d * (1 + g) / (r - g), dividend_ttm=d, paying_years=m["paying_years"])
    raise ValueError(name)


def methods_for(names, m: dict, peers: dict, s: Settings) -> list[dict]:
    return [_method(n, m, peers, s) for n in names]


def value_ticker(symbol: str, sector: str | None, m: dict | None, price: Decimal | None, peers: dict, s: Settings) -> dict:
    sector = sector or UNCLASSIFIED
    names = SECTOR_METHODS.get(sector, DEFAULT_METHODS)
    row = {"symbol": symbol, "sector": sector, "price": str(_vnd(price)) if price is not None else None, "fair": None, "low": None,
           "high": None, "gap": None, "verdict": "insufficient", "reason": None, "methods": [],
           "latest_year": m["latest_year"] if m else None, "latest_quarter": m["latest_quarter"] if m else None}
    if m is None:
        return {**row, "reason": "Chưa có báo cáo tài chính"}
    row["methods"] = methods_for(names, m, peers, s)
    values = [x["value"] for x in row["methods"] if x["value"] is not None]
    if len(values) < 2:
        return {**row, "reason": "Ít hơn 2 phương án đủ dữ liệu"}
    fair = _vnd(_median(values))
    row.update(fair=str(fair), low=str(min(values)), high=str(max(values)))
    if price is None:
        return {**row, "reason": "Chưa có giá"}
    gap = price / fair - 1
    verdict = "cheap" if gap <= -s.threshold else "expensive" if gap >= s.threshold else "fair"
    return {**row, "gap": str(gap.quantize(Decimal("0.0001"), ROUND_HALF_UP)), "verdict": verdict}


def reference_board(symbols, *, sectors, records, prices, year_end, settings: Settings, today: date, held: set[str]) -> dict:
    ms = {s: metrics(records[s], today=today, year_end_prices=year_end.get(s, {})) if records.get(s) else None for s in symbols}
    current = {}
    for s, m in ms.items():
        p = prices.get(s)
        if m and p:
            current[s] = {"pe": p / m["eps_ttm"] if m["eps_ttm"] and m["eps_ttm"] > 0 else None,
                          "pb": p / m["bvps"] if m["bvps"] and m["bvps"] > 0 else None}
    rows = []
    for s in symbols:
        sector = sectors.get(s)
        mates = [o for o in symbols if o != s and sector and sectors.get(o) == sector and o in current]
        peers = {k: [current[o][k] for o in mates if current[o][k] is not None] for k in ("pe", "pb")}
        rows.append({**value_ticker(s, sector, ms[s], prices.get(s), peers, settings), "held": s in held})
    return {"as_of": today.isoformat(), "rows": rows,
            "settings": {"required_return": str(settings.required_return), "long_term_growth": str(settings.long_term_growth),
                         "threshold": str(settings.threshold.normalize())}}
```

Notes:
- `_result` stringifies Decimal inputs; method `value` stays a `Decimal` until the route serializes the response (the route dumps every `value` with `str`). The tests compare `value` with a `Decimal`, so keep it a `Decimal` inside this module.
- Check `str(Decimal("0.20").normalize()) == "0.2"`, which matches the board test.

**Step 4:** Run the tests and expect 7 passed. If a hand-computed value is off by one đồng, recompute it by hand before changing the rounding. Then run the full suite.

**Step 5:** Commit `feat: reference valuation methods by sector`.

---

### Task 3: Throttled statement sync and CLI

**Files:**
- Modify: `backend/src/investment_agent/market/providers/vnstock_adapter.py` (add `fundamentals_frames`; `company` constructor parameter)
- Modify: `backend/src/investment_agent/market/fundamentals.py` (add `sync_fundamentals`)
- Modify: `backend/src/investment_agent/cli.py` (`fundamentals-sync`)
- Modify: `scripts/windows/run-after-close.ps1` (runs from 20:00 with `--limit 8`; keep the BOM)
- Test: `backend/tests/market/test_fundamentals.py` (append)

**Step 1: Failing tests** (append):

```python
from datetime import date, timedelta

from investment_agent.market.fundamentals import sync_fundamentals
from investment_agent.market.series import SeriesStore


class FakeProvider:
    def __init__(self, fail_once=()):
        self.calls, self.fail = [], set(fail_once)

    def fundamentals_frames(self, symbol):
        self.calls.append(("frames", symbol))
        if symbol in self.fail:
            self.fail.discard(symbol)
            raise RuntimeError("60/60 lượt gọi")
        return FRAMES

    def fetch_closes(self, symbol, start, end, *, interval, index):
        self.calls.append(("closes", symbol, start))
        return [(datetime(2025, 12, 31), "26")]


def test_sync_refreshes_the_stalest_tickers_and_their_daily_closes(tmp_path):
    store, series, p, waits = FundamentalsStore(tmp_path / "f"), SeriesStore(tmp_path / "s"), FakeProvider(fail_once={"MBB"}), []
    out = sync_fundamentals(store, series, ["MBB", "FPT", "VCB"], provider=p, now=NOW, limit=2, sleep=waits.append)
    assert out == {"updated": ["FPT", "MBB"], "errors": {}} or out == {"updated": ["MBB", "FPT"], "errors": {}}
    assert store.read("VCB") is None and 65 in waits  # MBB failed once, waited, then succeeded
    assert ("closes", "FPT", NOW.date() - timedelta(days=2920)) in p.calls and series.read("FPT-1d")


def test_sync_records_a_second_failure_and_moves_on(tmp_path):
    class Broken(FakeProvider):
        def fundamentals_frames(self, symbol):
            raise RuntimeError("down")
    out = sync_fundamentals(FundamentalsStore(tmp_path / "f"), SeriesStore(tmp_path / "s"), ["MBB"], provider=Broken(), now=NOW, limit=8,
                            sleep=lambda s: None)
    assert out == {"updated": [], "errors": {"MBB": "error:RuntimeError"}}


def test_cli_fundamentals_sync_reads_the_watchlist(tmp_path, capsys):
    from investment_agent.cli import fundamentals_sync
    (tmp_path / "market-symbols.txt").write_text("FPT\n", encoding="utf-8")
    assert fundamentals_sync(tmp_path, limit=8, provider=FakeProvider(), now=NOW, sleep=lambda s: None) == 0
    assert '"updated": ["FPT"]' in capsys.readouterr().out
```

**Step 2:** Run the tests and expect ImportError (`sync_fundamentals`).

**Step 3: Implement**
- In `fundamentals.py`, add:

```python
import time
from datetime import timedelta

PACE_SECONDS, RETRY_WAIT_SECONDS = 15, 65


def _with_retry(call, sleep):
    try:
        return call()
    except Exception:
        sleep(RETRY_WAIT_SECONDS)  # usually the 60-calls-per-minute limit
        return call()


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
            store.save(build_record(sym, frames, now))
            updated.append(sym)
        except Exception as exc:  # one ticker never stops the others
            errors[sym] = f"error:{type(exc).__name__}"
    return {"updated": updated, "errors": errors}
```

- In `VnstockProvider`, extend `__init__` with `company=None` (store it as `self._company`) and add:

```python
    def fundamentals_frames(self, symbol: str) -> dict:
        """Annual and quarterly income statement and balance sheet rows (long format) plus company events."""
        _, fundamental = self._api()
        eq = fundamental.equity(symbol.upper())
        if self._company is None:
            try:
                from vnstock import Company
            except ImportError as exc:
                raise ProviderUnavailable("vnstock is not installed; install it from vnstocks.com with your own key") from exc
            self._company = lambda sym: Company(source="VCI", symbol=sym)
        frames = {"income_year": eq.income_statement(period="year", format="long"), "balance_year": eq.balance_sheet(period="year", format="long"),
                  "income_quarter": eq.income_statement(period="quarter", format="long"),
                  "balance_quarter": eq.balance_sheet(period="quarter", format="long"), "events": self._company(symbol.upper()).events()}
        return {k: v.to_dict("records") for k, v in frames.items()}
```

- In `cli.py`, add a parser `fundamentals-sync` with `--data-dir` (required), `--limit` (int, default 8) and `--all` (store_true), dispatching to `fundamentals_sync(args.data_dir, limit=None if args.all else args.limit)`. Add the function:

```python
def fundamentals_sync(data_dir: Path, *, limit: int | None, provider=None, now=None, sleep=None) -> int:
    import time
    from datetime import datetime, timezone
    from investment_agent.market.fundamentals import FundamentalsStore, sync_fundamentals
    from investment_agent.market.providers.vnstock_adapter import VnstockProvider
    from investment_agent.market.series import SeriesStore
    from investment_agent.market.watchlist import load_watchlist
    out = sync_fundamentals(FundamentalsStore(data_dir / "fundamentals"), SeriesStore(data_dir / "trend-sources"), list(load_watchlist(data_dir).symbols),
                            provider=provider or VnstockProvider(), now=now or datetime.now(timezone.utc), limit=limit, sleep=sleep or time.sleep)
    print(json.dumps(out, ensure_ascii=False))
    return 1 if out["errors"] else 0
```

- In `run-after-close.ps1`, after the `trend-run` block (use the Edit tool):

```powershell
# Statements for the Định giá page: from the 20:00 slot, refresh the 8 stalest tickers (about 3 minutes, paced for Vnstock's limit).
if ((Get-Date).Hour -ge 20) {
    $fund = & $python -W ignore -m investment_agent.cli fundamentals-sync --data-dir $data --limit 8 2>$null
    "$(Get-Date -Format o) fundamentals-sync exit=$LASTEXITCODE $fund" | Add-Content -LiteralPath $log -Encoding UTF8
}
```

**Step 4:** Run the tests and expect them to pass. Run the full suite. The PowerShell parser must report 0 errors.

**Step 5:** Commit `feat: paced statement sync for the reference valuation`.

---

### Task 4: Valuation settings (Firestore `settings/valuation`)

**Files:**
- Modify: `backend/src/investment_agent/services/records.py` (add `ValuationSettings`, `valuation_settings`)
- Modify: `backend/src/investment_agent/api/routes/settings.py` (`GET`/`PUT /internal/settings/valuation`)
- Test: `backend/tests/api/test_valuation_settings_route.py`

**Step 1: Failing tests**

```python
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import Clock, call, make_client


def test_defaults_then_owner_update(tmp_path):
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    got = call(c, clock, "GET", "/internal/settings/valuation").json()
    assert got == {"version": 0, "settings": {"required_return": "0.13", "long_term_growth": "0.05", "threshold": "0.2"}}
    body = {"settings": {"required_return": "0.14", "long_term_growth": "0.05", "threshold": "0.15"}, "expected_version": 0, "request_id": "v1"}
    assert call(c, clock, "PUT", "/internal/settings/valuation", body).json()["version"] == 1
    assert call(c, clock, "GET", "/internal/settings/valuation").json()["settings"]["threshold"] == "0.15"


def test_required_return_must_exceed_growth_and_threshold_must_be_sensible():
    clock = Clock()
    c = make_client(clock, PersonalRepository("owner-1", MemoryDocumentStore()))
    for bad in ({"required_return": "0.05", "long_term_growth": "0.05", "threshold": "0.2"},
                {"required_return": "0.13", "long_term_growth": "0.05", "threshold": "0"}):
        assert call(c, clock, "PUT", "/internal/settings/valuation", {"settings": bad, "expected_version": 0, "request_id": "v2"}).status_code == 422
```

**Step 2:** Run the tests and expect 404 or 405.

**Step 3: Implement** in `services/records.py`:

```python
class ValuationSettings(ContractModel):
    required_return: Ratio = Decimal("0.13")
    long_term_growth: Ratio = Decimal("0.05")
    threshold: Ratio = Decimal("0.2")

    @model_validator(mode="after")
    def _sensible(self):
        if self.required_return <= self.long_term_growth:
            raise ValueError("required return must exceed long-term growth")
        if not Decimal("0") < self.threshold < Decimal("1"):
            raise ValueError("threshold must be between 0 and 1")
        return self


def valuation_settings(repo, owner) -> tuple[ValuationSettings, int]:
    record = read_version(repo, owner, "settings", "valuation", None)
    return (ValuationSettings.model_validate(record.payload), record.version) if record else (ValuationSettings(), 0)
```

Add the imports `from decimal import Decimal` and `from pydantic import model_validator` where missing. In `settings.py`, add `ValuationRequest` and the two routes, mirroring `trading`. The GET returns `{"version": v, "settings": settings.model_dump(mode="json")}` using `valuation_settings`.

**Step 4:** Run the tests and expect them to pass, then the full suite.

**Step 5:** Commit `feat: owner valuation settings`.

---

### Task 5: API `GET /internal/fairvalue`

**Files:**
- Create: `backend/src/investment_agent/api/routes/fairvalue.py`
- Modify: `backend/src/investment_agent/api/routes/watchlist.py` (extract `held_tickers(request) -> set[str]` from `_rows`, so `_rows` uses it)
- Modify: `backend/src/investment_agent/api/app.py` (register the router)
- Modify: `apps/web/src/lib/server/python-proxy.ts` (add `"fairvalue"` to `AREAS`)
- Test: `backend/tests/api/test_fairvalue_route.py`

**Step 1: Failing test**

```python
import json
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from investment_agent.api.app import create_app
from investment_agent.api.auth import InternalAuthSettings
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.series import SeriesStore
from investment_agent.market.view import PricePoint, SyntheticMarket
from investment_agent.repositories.personal import MemoryDocumentStore, PersonalRepository

from signed_client import SECRET, TOKEN, Clock, call


def test_fairvalue_lists_every_watched_ticker_with_methods(tmp_path):
    (tmp_path / "market-symbols.txt").write_text("FPT\nVCB\n", encoding="utf-8")
    (tmp_path / "industries.json").write_text(json.dumps({"as_of": "2026-10-25", "source": "t", "level": 2,
                                                         "sectors": {"FPT": "Công nghệ Thông tin", "VCB": "Ngân hàng"}}), encoding="utf-8")
    years = {str(y): {"npat": "1000000000", "eps": "1000", "equity": "10000000000"} for y in range(2020, 2026)}
    quarters = {q: {"npat": "250000000", "equity": "10000000000"} for q in ("2025-Q2", "2025-Q3", "2025-Q4", "2026-Q1", "2026-Q2")}
    divs = [{"date": f"{y}-07-01", "cash": "500"} for y in range(2021, 2026)] + [{"date": "2026-07-01", "cash": "500"}]
    FundamentalsStore(tmp_path / "fundamentals").save({"symbol": "FPT", "fetched_at": "2026-10-26T00:00:00+00:00", "source": "t",
                                                      "years": years, "quarters": quarters, "dividends": divs, "issues": []})
    SeriesStore(tmp_path / "trend-sources").upsert("FPT-1d", [(datetime(y, 12, 31), "12") for y in range(2020, 2026)])
    market = SyntheticMarket(prices={"FPT": PricePoint(Decimal(9000), date(2027, 1, 14))})
    clock = Clock()
    app = create_app(InternalAuthSettings("owner-1", TOKEN, SECRET), clock=clock, personal_repository=PersonalRepository("owner-1", MemoryDocumentStore()),
                     market=market, data_dir=tmp_path)
    body = call(TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 50000)), clock, "GET", "/internal/fairvalue").json()
    rows = {r["symbol"]: r for r in body["rows"]}
    assert rows["FPT"]["fair"] is not None and rows["FPT"]["verdict"] in {"cheap", "fair", "expensive"}
    assert all(isinstance(m["value"], (str, type(None))) for m in rows["FPT"]["methods"])
    assert rows["VCB"]["verdict"] == "insufficient" and rows["VCB"]["reason"] == "Chưa có báo cáo tài chính"
    assert body["settings"]["threshold"] == "0.2"
```

In this case FPT has P/E 12 every year (12,000 × 1m shares / 1bn) and EPS TTM 1,000, so `pe_history` = 12,000 and `ddm` = 500 × 1.05 / 0.08 = 6,563. The median is 9,281, so at 9,000 the verdict is fair. `pe_peers` does not apply (no peers).

**Step 2:** Run it and expect 404.

**Step 3: Implement `fairvalue.py`**

```python
"""Reference valuation of the watched tickers (Định giá page): computed on request from stored statements."""

from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import valuation_settings
from investment_agent.valuation.reference import Settings, reference_board, year_end_prices

from ..auth import require_owner
from .common import now, unavailable
from .watchlist import held_tickers

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


@router.get("/fairvalue")
def fairvalue(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir = request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    try:
        settings, _ = valuation_settings(repo, owner)
        held = held_tickers(request)
    except RepositoryUnavailable:
        return unavailable()
    data_dir, today, market = Path(data_dir), now(request).astimezone(VN).date(), request.app.state.market
    symbols = list(load_watchlist(data_dir).symbols)
    store, series = FundamentalsStore(data_dir / "fundamentals"), SeriesStore(data_dir / "trend-sources")
    records = {s: store.read(s) for s in symbols}
    prices = {s: p.price for s in symbols if (p := market.price(s)) is not None}
    board = reference_board(symbols, sectors=load_sectors(data_dir)[0], records=records, prices=prices,
                            year_end={s: year_end_prices(series.read(f"{s}-1d"), today=today) for s in symbols},
                            settings=Settings(settings.required_return, settings.long_term_growth, settings.threshold), today=today, held=held)
    for row in board["rows"]:
        for m in row["methods"]:
            m["value"] = str(m["value"]) if m["value"] is not None else None
    return board
```

Extract `held_tickers` in `watchlist.py`:

```python
def held_tickers(request: Request) -> set[str]:
    """Tickers with shares in the owner's ledger; raises RepositoryUnavailable."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    book = LedgerBook(read_version(repo, owner, "ledger_events", "main", None))
    return {p.security_id for p in replay(list(book.effective().events)).positions if p.quantity + p.pending_quantity > 0}
```

Then make `_rows` call it. Register the router in `app.py` and add `"fairvalue"` to the proxy `AREAS`.

**Step 4:** Run the test and expect it to pass, then the full suite.

**Step 5:** Commit `feat: reference valuation API`.

---

### Task 6: Page "Định giá" and settings section

**Files:**
- Create: `apps/web/src/components/fair-value-view.tsx`
- Create: `apps/web/src/app/(private)/fair-value/page.tsx`
- Modify: `apps/web/src/components/app-nav.tsx` (link `/fair-value` labelled "Định giá", lucide icon `Scale`, after "Theo dõi")
- Modify: `apps/web/src/components/settings-view.tsx` (section "Định giá tham khảo": three percent inputs, saved with `PUT settings/valuation`)
- Modify: `apps/web/src/app/globals.css` (responsive table that becomes cards under 700px)
- Modify: `tests/e2e/fixture_backend.py` (fundamentals for FPT and VCB, year-end series, industries entry for VCB already present)
- Test: `tests/e2e/fair-value.spec.ts`

**Step 1: Fixture.**
- In `fixture_backend.py`, before `create_app`, save one FPT record with the same numbers as the Task 5 test. Write it with `FundamentalsStore(os.path.join(data, "fundamentals")).save(...)`.
- Add year-end closes with `SeriesStore(os.path.join(data, "trend-sources")).upsert("FPT-1d", [(datetime(y, 12, 31), "12") for y in range(2020, 2026)])`.
- The fixture market prices FPT at 60,000. The fair median is about 9,281, so FPT reads **Đắt**.
- VCB has no statements, so it reads "Chưa có báo cáo tài chính".
- Import `datetime` and the stores.

**Step 2: Failing e2e**

```ts
import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// Synthetic fixture data only: FPT has statements (P/E 12 every year, cash dividends), VCB has none.
test.beforeEach(async ({ context }) => signIn(context));

async function openPage(page: import("@playwright/test").Page) {
  await page.goto("/fair-value");
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
}

test("each watched ticker gets a fair-value range and a verdict, with the methods behind it", async ({ page }) => {
  await openPage(page);
  const table = page.getByRole("table", { name: "Định giá tham khảo" });
  const fpt = table.getByRole("row", { name: /FPT/ });
  await expect(fpt).toContainText("Đắt");
  await expect(table.getByRole("row", { name: /VCB/ })).toContainText("Chưa có báo cáo tài chính");
  await fpt.getByRole("button", { name: "Chi tiết FPT" }).click();
  const detail = page.getByRole("region", { name: "Phương án định giá FPT" });
  await expect(detail).toContainText("P/E lịch sử");
  await expect(detail).toContainText("12.000");
  await expect(detail).toContainText("Cần ít nhất 3 mã cùng ngành có số liệu");
  await expect(page.getByText(/không phải khuyến nghị/)).toBeVisible();
  await expect(page.getByText(/lợi suất yêu cầu 13%/)).toBeVisible();
});

test("no horizontal scroll on the valuation page at 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 900 });
  await openPage(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  const scrollers = await page.evaluate(() => [...document.querySelectorAll("main *")]
    .filter((el) => el.scrollWidth > el.clientWidth + 1 && ["auto", "scroll"].includes(getComputedStyle(el).overflowX)).length);
  expect(scrollers).toBe(0);
});
```

**Step 3:** Run `cd apps/web && npx playwright test fair-value --reporter=line` and expect the first test to fail (page missing).

**Step 4: Implement**

`fair-value-view.tsx`:
```tsx
"use client";
import { Fragment, useEffect, useMemo, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatRatio, formatVnd } from "../lib/format";

type Method = { method: string; label: string; value: string | null; reason: string | null; inputs: Record<string, string | number> };
type Row = { symbol: string; sector: string; price: string | null; fair: string | null; low: string | null; high: string | null; gap: string | null;
  verdict: "cheap" | "fair" | "expensive" | "insufficient"; reason: string | null; methods: Method[]; latest_year: string | null;
  latest_quarter: string | null; held: boolean };
type Board = { as_of: string; rows: Row[]; settings: { required_return: string; long_term_growth: string; threshold: string } };

const VERDICT: Record<Row["verdict"], { label: string; tone: string }> = {
  cheap: { label: "Rẻ", tone: "good" }, fair: { label: "Hợp lý", tone: "" }, expensive: { label: "Đắt", tone: "bad" },
  insufficient: { label: "Chưa đủ dữ liệu", tone: "warn" },
};
const INPUT: Record<string, string> = { eps: "EPS", bvps: "Giá trị sổ sách/cp", pe_median: "P/E trung vị", pb_median: "P/B trung vị", years: "Số năm",
  base: "Cơ sở", peer_median: "Trung vị cùng ngành", peers: "Số mã cùng ngành", roe: "ROE", justified_pb: "P/B hợp lý",
  dividend_ttm: "Cổ tức tiền 12 tháng", paying_years: "Số năm trả cổ tức" };
const pct = (v: string) => formatRatio(v, 1);

function inputText(k: string, v: string | number) {
  if (typeof v === "number") return String(v);
  if (k === "roe" || k === "justified_pb" || k.endsWith("median")) return k === "roe" ? pct(v) : v.replace(".", ",").slice(0, 6);
  return formatVnd(v);
}

export function FairValueView() {
  const [board, setBoard] = useState<Board | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  useEffect(() => { api<Board>("fairvalue").then(setBoard, (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải.")); }, []);
  const rows = useMemo(() => (board?.rows ?? []).filter((r) => filter === "all" || (filter === "held" ? r.held : r.verdict === filter))
    .sort((a, b) => (a.gap === null ? 1 : b.gap === null ? -1 : Number(a.gap) - Number(b.gap))), [board, filter]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!board) return <p className="muted">Đang tải…</p>;
  const s = board.settings;
  return (
    <section className="surface">
      <p className="notice">Định giá tham khảo từ báo cáo tài chính công bố (Vnstock, gói miễn phí), không phải khuyến nghị. Lợi suất yêu cầu {pct(s.required_return)},
        tăng trưởng dài hạn {pct(s.long_term_growth)}, ngưỡng Rẻ/Đắt ±{pct(s.threshold)} so với giá hợp lý (trung vị các phương án). Sửa trong Cài đặt.</p>
      <div className="actions" role="radiogroup" aria-label="Lọc">
        {[["all", "Tất cả"], ["cheap", "Rẻ"], ["fair", "Hợp lý"], ["expensive", "Đắt"], ["insufficient", "Chưa đủ dữ liệu"], ["held", "Đang nắm"]].map(([id, label]) => (
          <label key={id} className="choice"><input type="radio" name="fv-filter" checked={filter === id} onChange={() => setFilter(id)} />{label}</label>))}
      </div>
      <table className="fv-table" aria-label="Định giá tham khảo">
        <thead><tr><th>Mã</th><th>Ngành</th><th className="num">Giá</th><th className="num">Giá hợp lý</th><th className="num">Chênh lệch</th><th>Kết luận</th><th>Số liệu</th><th /></tr></thead>
        <tbody>{rows.map((r) => (
          <Fragment key={r.symbol}>
            <tr>
              <td data-label="Mã"><strong>{r.symbol}</strong>{r.held && <> <span className="pill good">Đang nắm</span></>}</td>
              <td data-label="Ngành">{r.sector}</td>
              <td data-label="Giá" className="num">{formatVnd(r.price)}</td>
              <td data-label="Giá hợp lý" className="num">{r.fair ? <>{formatVnd(r.fair)}<div className="caption">{formatVnd(r.low, { unit: false })} – {formatVnd(r.high, { unit: false })}</div></> : "—"}</td>
              <td data-label="Chênh lệch" className="num">{r.gap ? `${r.gap.startsWith("-") ? "" : "+"}${pct(r.gap)}` : "—"}</td>
              <td data-label="Kết luận"><span className={`pill ${VERDICT[r.verdict].tone}`}>{VERDICT[r.verdict].label}</span>{r.reason && <div className="caption">{r.reason}</div>}</td>
              <td data-label="Số liệu">{r.latest_quarter ?? "—"}</td>
              <td><button className="btn" aria-expanded={open === r.symbol} onClick={() => setOpen(open === r.symbol ? null : r.symbol)}
                aria-label={`Chi tiết ${r.symbol}`}>Chi tiết</button></td>
            </tr>
            {open === r.symbol && <tr className="fv-detail"><td colSpan={8}>
              <section aria-label={`Phương án định giá ${r.symbol}`}>
                {r.methods.length === 0 && <p className="muted">{r.reason}</p>}
                <ul>{r.methods.map((m) => (
                  <li key={m.method}><strong>{m.label}</strong>: {m.value ? formatVnd(m.value) : <span className="muted">Không áp dụng — {m.reason}</span>}
                    {m.value && <span className="caption"> ({Object.entries(m.inputs).map(([k, v]) => `${INPUT[k] ?? k} ${inputText(k, v)}`).join(" · ")})</span>}</li>))}
                </ul>
                <p className="caption">Số cổ phiếu ước tính từ lợi nhuận / EPS năm {r.latest_year ?? "—"} và các đợt phát hành sau đó; có thể lệch vài phần trăm.</p>
              </section>
            </td></tr>}
          </Fragment>))}
        </tbody>
      </table>
    </section>
  );
}
```

`page.tsx`:
```tsx
import { FairValueView } from "../../../components/fair-value-view";

export default function FairValuePage() {
  return (
    <>
      <div className="pagehead"><h1>Giá hiện tại rẻ hay đắt?</h1><p className="muted">Nhiều phương án định giá theo ngành cho các mã đang theo dõi, để tham khảo.</p></div>
      <FairValueView />
    </>
  );
}
```

CSS (append):
```css
.fv-table{width:100%;border-collapse:collapse;font-size:14px}
.fv-table th,.fv-table td{padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}
.fv-detail ul{margin:6px 0;padding-left:18px}.fv-detail li{margin:4px 0}
.pill.bad{background:#fbe9ea;color:#9c2f36}
@media (max-width:700px){
  .fv-table thead{display:none}
  .fv-table,.fv-table tbody,.fv-table tr,.fv-table td{display:block;width:100%}
  .fv-table tr{border:1px solid var(--line);border-radius:8px;margin:0 0 10px;padding:6px 10px}
  .fv-table td{border:0;padding:4px 0;text-align:left}
  .fv-table td[data-label]::before{content:attr(data-label) ": ";color:var(--muted);font-size:12px}
}
```

If `.pill.bad` already exists from the macro page, skip that line.

Settings section in `settings-view.tsx`:
- Load `api<{version:number;settings:{required_return:string;long_term_growth:string;threshold:string}}>("settings/valuation")` together with the others.
- Show three inputs in percent, labelled "Lợi suất yêu cầu (%/năm)", "Tăng trưởng dài hạn (%/năm)" and "Ngưỡng Rẻ/Đắt (%)". Convert each with `percentToRatio`.
- Save with `PUT settings/valuation`, body `{settings, expected_version, request_id: requestId()}`.

**Step 5:** Run `scripts\windows\verify.ps1` and expect every line to be PASS.

**Step 6:** Commit `feat: Định giá page and valuation settings`.

---

### Task 7: First load, PR (owner-gated) and spot check

1. Push the branch and open a PR. The body covers the methods by sector, the data used and its limits (no FCF DCF, no NAV, estimated shares), and the tests with their RED runs.
2. After the owner approves the merge, fast-forward the main checkout, rebuild and restart.
3. Run the first load in the main checkout: `fundamentals-sync --data-dir data --all`. It takes about 30–60 minutes, so run it in the background and report when done.
4. Spot-check MBB, KDH, HPG and FPT against their published statements: shares, EPS TTM and BVPS. Report each ticker's verdict and the methods that did not apply.
