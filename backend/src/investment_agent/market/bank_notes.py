"""Thuyết minh ngân hàng: loans by quality group and customer deposits by kind, per quarter, from the notes to each watched
bank's statements on Vietcap's IQ API (public, no key; the source the owner approved on 08/11/2026, since VNDirect publishes no
note figures and Vnstock's Community tier locks them). From them the bank ratios table shows the group-2 share and CASA.

Vietcap's robots.txt asks for 10 seconds between requests, and its notes answer 418 to faster callers (now and then even to
slower ones): two calls per bank (the notes, and statistics-financial for the year-end CAR), 10 seconds apart, a refused call
tried once more after 30 seconds, under this application's own name; a bank's record is refreshed at most weekly. A ratio is given only where
the parts add up to the total Vietcap prints with them; otherwise it is left blank and the two figures are reported.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

URL = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/{symbol}/financial-statement?section=NOTE"
STATS_URL = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/{symbol}/statistics-financial"
RETRY_SECONDS = 30
SOURCE = "vietcap:iq"
DELAY_SECONDS = 10  # robots.txt Crawl-delay
MAX_AGE = timedelta(days=7)
BANK = "Ngân hàng"
# Vietcap's note fields (NOTE section of /financial-statement/metrics): loans by quality and deposits by kind.
FIELDS = {"loans": "nob39", "group1": "nob40", "group2": "nob41", "group3": "nob42", "group4": "nob43", "group5": "nob44",
          "deposits": "nob65", "demand": "nob66", "term": "nob67", "savings": "nob68", "margin": "nob69", "special": "nob70"}
GROUPS = ("group1", "group2", "group3", "group4", "group5")
DEPOSIT_PARTS = ("demand", "term", "savings", "margin", "special")
_QUARTER_END = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")
_Q4 = Decimal("0.0001")


class BankNoteStore:
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


def _whole(value) -> str | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return format(d.to_integral_value(ROUND_HALF_UP), "f") if d.is_finite() else None


def parse_notes(text: str, *, symbol: str) -> dict[str, dict[str, str]]:
    """{quarter-end date: {field: amount in whole đồng}}; annual rows and missing figures left out."""
    body = json.loads(text)
    rows = ((body.get("data") or {}).get("quarters")) or []
    out = {}
    for row in rows:
        if str(row.get("ticker", symbol)).upper() != symbol.upper() or row.get("lengthReport") not in _QUARTER_END:
            continue
        values = {name: v for name, code in FIELDS.items() if (v := _whole(row.get(code))) is not None}
        if values:
            out[f"{int(row['yearReport'])}-{_QUARTER_END[row['lengthReport']]}"] = values
    return dict(sorted(out.items()))


def parse_car_years(text: str) -> dict[str, str]:
    """Year-end CAR as a ratio by year, from the yearly rows (quarter 5); the quarterly rows carry 0.0 for "not given", and a
    zero is never a capital adequacy ratio, so it is left out."""
    rows = json.loads(text).get("data") or []
    out = {}
    for row in rows:
        if row.get("quarter") != 5 or not row.get("year"):
            continue
        try:
            value = Decimal(str(row.get("car")))
        except (InvalidOperation, TypeError, ValueError):
            continue
        if value.is_finite() and value > 0:
            out[str(int(row["year"]))] = format(value.normalize(), "f")
    return dict(sorted(out.items()))


def _million(d: Decimal) -> str:
    """Đồng as the notes print them, in triệu đồng: 1.288.128.443."""
    return f"{int((d / 1_000_000).to_integral_value(ROUND_HALF_UP)):,}".replace(",", ".")


def note_ratios(quarter: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Group-2 share of loans and CASA, each only where its parts add up to Vietcap's total; and why any is left blank."""
    q = {k: Decimal(v) for k, v in quarter.items()}
    ratios, problems = {}, []
    if all(g in q for g in GROUPS) and q.get("loans"):
        added = sum(q[g] for g in GROUPS)
        if added == q["loans"]:
            ratios["group2_ratio"] = str((q["group2"] / added).quantize(_Q4, ROUND_HALF_UP))
        else:
            problems.append(f"nợ nhóm 1–5 cộng ra {_million(added)}, khác tổng dư nợ {_million(q['loans'])} triệu đồng")
    if "demand" in q and "margin" in q and q.get("deposits"):
        added = sum(q.get(p, Decimal(0)) for p in DEPOSIT_PARTS)
        if added == q["deposits"]:
            ratios["casa"] = str(((q["demand"] + q["margin"]) / q["deposits"]).quantize(_Q4, ROUND_HALF_UP))
        else:
            problems.append(f"các loại tiền gửi cộng ra {_million(added)}, khác tổng tiền gửi {_million(q['deposits'])} triệu đồng")
    return ratios, problems


def bank_ratio_rows(entered: dict[str, dict], notes: dict[str, dict]) -> dict[str, dict[str, tuple[str, str]]]:
    """{"2026-Q3": {"casa" | "group2_ratio": (ratio, source)}}: Vietcap's where its parts add up to its totals, with the quarters the
    owner entered (Số liệu ngân hàng) on top; the source is "Vietcap" or "số nhập tay"."""
    from investment_agent.domain.bank_figures import derive
    rows: dict[str, dict[str, tuple[str, str]]] = {}
    for day, quarter in notes.items():
        ratios, _ = note_ratios(quarter)
        rows[f"{day[:4]}-Q{(int(day[5:7]) + 2) // 3}"] = {key: (value, "Vietcap") for key, value in ratios.items()}
    for quarter, values in entered.items():
        derived = derive(values)
        for key in ("casa", "group2_ratio"):
            if derived[key] is not None:
                rows.setdefault(quarter, {})[key] = (derived[key], "số nhập tay")
    return {q: row for q, row in sorted(rows.items()) if row}


def sync_bank_notes(store: BankNoteStore, sectors: dict[str, str | None], *, get: Callable[[str], str],
                    sleep: Callable[[float], None] = time.sleep, now: datetime | None = None, force: bool = False) -> dict[str, str]:
    """Refresh each watched bank whose record is a week old or missing; one failing is reported, the others still update."""
    now = now or datetime.now(timezone.utc)
    results, called = {}, False

    def fetch(url: str) -> str:
        nonlocal called
        if called:
            sleep(DELAY_SECONDS)
        called = True
        try:
            return get(url)
        except Exception:
            sleep(RETRY_SECONDS)
            return get(url)

    for symbol in sorted(s for s, sector in sectors.items() if sector == BANK):
        old = store.read(symbol)
        if old and not force and "car_years" in old and now - datetime.fromisoformat(old["fetched_at"]) < MAX_AGE:
            results[symbol] = "fresh"
            continue
        try:
            quarters = parse_notes(fetch(URL.format(symbol=symbol)), symbol=symbol)
        except Exception as exc:
            results[symbol] = f"error:{type(exc).__name__}"
            continue
        if not quarters:
            results[symbol] = "error:no_observations"
            continue
        record = {"symbol": symbol, "fetched_at": now.isoformat(), "source": SOURCE, "quarters": quarters}
        try:
            record["car_years"] = parse_car_years(fetch(STATS_URL.format(symbol=symbol)))
            results[symbol] = "ok"
        except Exception as exc:  # the notes are kept; without "car_years" the bank is due again on the next run
            if old and "car_years" in old:
                record["car_years"] = old["car_years"]
            results[symbol] = f"error:car:{type(exc).__name__}"
        store.save(record)
    return results
