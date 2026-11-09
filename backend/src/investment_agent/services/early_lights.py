"""Bảng đèn chỉ báo sớm: indicators the owner picks for a ticker (macro, commodities, the ticker's own ratios) against thresholds the owner
sets, coloured Xấu / Theo dõi / Tốt, with a Telegram note when a colour changes. Thresholds are the owner's opinion; the application adds
none. A series too old, or a figure missing, gets no colour. Rules are personal settings; never sent to a model."""

import json
import os
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable

from investment_agent.market.bank_notes import BankNoteStore, bank_ratio_rows
from investment_agent.market.financial_ratios import FinancialRatioStore, kind_of
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.leading import MacroStore, load_indicators
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.statements import StatementStore
from investment_agent.market.valuation_check import ValuationCheckStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.services.records import read_version
from investment_agent.valuation.peer_compare import COLUMNS
from investment_agent.valuation.statement_table import statement_table

MAX_RULES = 12
STALE_DAYS = 120  # a monthly series can lag a couple of months; older than this says nothing about today
STATE_FILE = ("alerts", "lights.json")
STATES = {"bad": "Xấu", "watch": "Theo dõi", "good": "Tốt"}
_COMMODITIES = {"com_coal": "Giá than", "com_iron_ore": "Giá quặng sắt", "com_rubber": "Giá cao su", "com_sugar": "Giá đường", "com_shrimp": "Giá tôm", "com_lng": "Giá LNG",
                "com_aluminium": "Giá nhôm", "com_copper": "Giá đồng", "com_wheat": "Giá lúa mì", "com_soybean": "Giá đậu tương"}
_VALUATION = {"pe", "pb", "ev_ebitda", "pe_now", "pb_now"}
_BANK_NOTE = {"CASA": "casa", "GROUP2_RATIO": "group2_ratio"}


def record_id(symbol: str) -> str:
    return f"lights_{symbol}"


def color(value: Decimal, bad: Decimal, good: Decimal) -> str:
    """Thresholds set the direction: good above bad means higher is better, good below bad means lower is better."""
    if good > bad:
        return "bad" if value < bad else "good" if value >= good else "watch"
    return "bad" if value > bad else "good" if value <= good else "watch"


def _stock_columns(kind: str | None) -> list[tuple[str, str, str]]:
    columns = [(k, label, fmt) for k, label, fmt, _, scope in COLUMNS[kind] if fmt != "money" and scope == "q"]
    columns += [("pe_now", "P/E theo giá", "x"), ("pb_now", "P/B theo giá", "x")]
    return columns + ([("roic", "ROIC vận hành 4 quý", "pct")] if kind is None else [])


def catalog(kind: str | None) -> list[dict]:
    macro = [{"id": f"macro:{i['id']}", "label": i.get("label") or i["id"], "tier": "Dẫn dắt", "unit": ""} for i in load_indicators()]
    macro += [{"id": f"macro:{k}", "label": v, "tier": "Dẫn dắt", "unit": ""} for k, v in _COMMODITIES.items()]
    stock = [{"id": f"stock:{k}", "label": label, "tier": "Định giá" if k in _VALUATION else "Kết quả", "unit": "%" if fmt.startswith("pct") else "x" if fmt == "x" else ""}
             for k, label, fmt in _stock_columns(kind)]
    return macro + stock


def _plain(d: Decimal) -> str:
    return format(d.quantize(Decimal("0.01")).normalize(), "f")


def _stock_values(repo, owner, data_dir: Path, symbol: str, kind: str | None) -> dict[str, tuple[Decimal, str]]:
    """Each column's latest figure and its period, percentages in percent as the owner's thresholds are written."""
    by_key: dict[str, tuple[str, str]] = {}

    def keep(key, period, value):
        if value is not None and (key not in by_key or period > by_key[key][0]):
            by_key[key] = (period, value)
    record = StatementStore(data_dir / ("statements" if kind is None else "statements-financial")).read(symbol)
    if record:
        fundamentals = FundamentalsStore(data_dir / "fundamentals").read(symbol) or {}
        table = statement_table(record, closes=SeriesStore(data_dir / "trend-sources").read(f"{symbol}-1d"), vnstock=fundamentals.get("quarters"), kind=kind, check=ValuationCheckStore(data_dir / "valuation-check").read(symbol))
        for row in table["quarters"]["rows"]:
            if row["key"]:
                for period, value in zip(table["quarters"]["periods"], row["values"]):
                    keep(row["key"], period, value)
        current = table.get("current") or {}
        day = current.get("close_date") or ""
        keep("pe_now", day, current.get("pe"))
        keep("pb_now", day, current.get("pb"))
        summary = table.get("summary") or {}
        keep("roic", summary.get("period") or "", summary.get("roic"))
    ratios = FinancialRatioStore(data_dir / "financial-ratios").read(symbol) if kind else None
    for day, values in ((ratios or {}).get("quarters") or {}).items():
        period = f"{day[:4]}-Q{(int(day[5:7]) + 2) // 3}"
        for key, value in values.items():
            keep(key, period, value)
    if kind == "bank":
        saved = read_version(repo, owner, "settings", f"bank_figures_{symbol}", None)
        entered = {q: v["values"] for q, v in saved.payload.get("quarters", {}).items()} if saved else {}
        rows = bank_ratio_rows(entered, (BankNoteStore(data_dir / "bank-notes").read(symbol) or {}).get("quarters") or {})
        for period, row in rows.items():
            for code, key in _BANK_NOTE.items():
                if key in row:
                    keep(code, period, row[key][0])
    formats = {k: fmt for k, _, fmt in _stock_columns(kind)}
    return {f"stock:{k}": ((Decimal(v) * 100 if formats[k].startswith("pct") else Decimal(v)), p) for k, (p, v) in by_key.items() if k in formats}


def symbol_lights(repo, owner, data_dir: Path, symbol: str, *, today: date) -> dict:
    data_dir = Path(data_dir)
    kind = kind_of(load_sectors(data_dir)[0].get(symbol))
    saved = read_version(repo, owner, "settings", record_id(symbol), None)
    rules = saved.payload.get("rules", []) if saved else []
    options = {c["id"]: c for c in catalog(kind)}
    stock = _stock_values(repo, owner, data_dir, symbol, kind) if any(r["id"].startswith("stock:") for r in rules) else {}
    limit = (today - timedelta(days=STALE_DAYS)).isoformat()
    rows = []
    for r in rules:
        info = options.get(r["id"])
        if info is None:
            continue
        value, day, note = None, None, None
        if r["id"].startswith("macro:"):
            points = MacroStore(data_dir).read(r["id"].split(":", 1)[1])
            if points:
                value, day = Decimal(points[-1]["value"]), points[-1]["date"]
                if day < limit:
                    note = f"Số cũ ({day}), không tô màu"
        elif r["id"] in stock:
            value, day = stock[r["id"]]
        bad, good = Decimal(r["bad"]), Decimal(r["good"])
        state = "none" if value is None or note else color(value, bad, good)
        rows.append({**info, "bad": r["bad"], "good": r["good"], "value": None if value is None else _plain(value), "date": day, "state": state,
                     "note": note or (None if value is not None else "Chưa có số liệu")})
    return {"symbol": symbol, "version": saved.version if saved else 0, "catalog": list(options.values()), "rows": rows}


def lights_check(repo, owner, data_dir: Path, *, send: Callable[[str], bool], today: date) -> dict:
    """A colour seen for the first time is only remembered; a later change is announced once, and again next run if sending failed."""
    data_dir = Path(data_dir)
    path = data_dir.joinpath(*STATE_FILE)
    known: dict = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    current, lines = {}, []
    for symbol in load_watchlist(data_dir).symbols:
        if read_version(repo, owner, "settings", record_id(symbol), None) is None:
            continue
        current[symbol] = {}
        for row in symbol_lights(repo, owner, data_dir, symbol, today=today)["rows"]:
            before = known.get(symbol, {}).get(row["id"])
            if row["state"] == "none":  # no reading now: keep the last colour, so a gap in the data is no change
                if before:
                    current[symbol][row["id"]] = before
                continue
            current[symbol][row["id"]] = row["state"]
            if before and before != row["state"]:
                lines.append(f"• {symbol} · {row['label']}: {STATES[before]} → {STATES[row['state']]} (hiện {row['value']})")
    sent = False
    if lines:
        sent = bool(send("Bảng đèn chỉ báo đổi màu\n" + "\n".join(lines) + "\nNgưỡng do bạn đặt. Không phải khuyến nghị."))
    if sent or not lines:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    return {"changes": len(lines), "sent": sent}
