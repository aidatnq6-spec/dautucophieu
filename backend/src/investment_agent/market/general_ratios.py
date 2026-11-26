"""Chỉ số tài chính doanh nghiệp thường: VNDirect's own quarterly ratios (v4/ratios) for every HOSE ticker outside banks, securities
firms and insurers, which keep their sector set in financial_ratios.py and data/financial-ratios.

Kept apart under data/financial-ratios-general so nothing the ticker page or the health score reads changes; Claude reads them through
the public-data MCP tool. One call per ticker for the codes below from 2017; each code's label is VNDirect's own itemName. A ticker
never fetched comes first, then those not refreshed for a week, oldest first, up to the limit of the run. Values are as VNDirect
works them out (ratios as fractions, days, times or đồng); rows for another ticker or code are dropped, nothing is filled in.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from .financial_ratios import FIRST_START, kind_of, parse_ratios

# Return, margins, balance-sheet strength, cash and working capital, growth and payout: quarter-end (AQ), quarter (QR) or four
# quarters (TR) as VNDirect names them. Checked against KDH at 30/09/2026 on 26/11/2026.
CODES = ("ROAE_TR_AVG4Q", "ROAA_TR_AVG4Q", "ROIC_TR_AVG4Q", "GROSS_MARGIN_QR", "GROSS_MARGIN_TR", "NET_MARGIN_TR", "OPERATING_EBIT_MARGIN_TR",
         "CURRENT_RATIO_AQ", "QUICK_RATIO_AQ", "DEBT_TO_EQUITY_AQ", "EQUITY_TO_ASSET_AQ", "NET_CASH_TO_EQUITY_AQ", "DEBT_EBITDA",
         "INTEREST_COVERAGE_TR", "CFO_TO_SALES_TR", "DSO_TR_AVG5Q", "DIO_TR_AVG5Q", "DPO_TR_AVG5Q", "CASH_CONVERSION_CYCLE_TR_AVG5Q",
         "EPS_TR", "BVPS_AQ", "NET_SALES_TR_GRYOY", "NET_PROFIT_TR_GRYOY", "EPS_TR_GR3YR", "DIVIDEND_PAYOUT_TR")
# Shown in Bảng số tài chính of a general company (owner, 26/11/2026; docs/superpowers/specs/2026-11-26-chi-so-doanh-nghiep-thuong-trang-ma-design.md)
GENERAL_DISPLAY = (("ROAE_TR_AVG4Q", "ROAE", "pct1"), ("ROAA_TR_AVG4Q", "ROAA", "pct2"), ("ROIC_TR_AVG4Q", "ROIC", "pct1"),
                   ("GROSS_MARGIN_TR", "Biên lợi nhuận gộp 4 quý", "pct1"), ("NET_MARGIN_TR", "Biên lợi nhuận ròng 4 quý", "pct1"),
                   ("CFO_TO_SALES_TR", "Dòng tiền kinh doanh / doanh thu 4 quý", "pct1"), ("DEBT_TO_EQUITY_AQ", "Nợ vay / vốn chủ", "times"),
                   ("CURRENT_RATIO_AQ", "Thanh toán hiện thời", "times"), ("INTEREST_COVERAGE_TR", "Khả năng trả lãi vay 4 quý", "times"),
                   ("DSO_TR_AVG5Q", "Số ngày phải thu", "days"), ("DIO_TR_AVG5Q", "Số ngày tồn kho", "days"),
                   ("CASH_CONVERSION_CYCLE_TR_AVG5Q", "Chu kỳ vận động vốn", "days"))
URL = "https://api-finfo.vndirect.com.vn/v4/ratios?q=code:{symbol}~ratioCode:{codes}~reportDate:gte:{start}&sort=reportDate:desc&size=2000"
SOURCE = "vndirect:finfo"
STALE = timedelta(days=7)
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


class GeneralRatioStore:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir) / "financial-ratios-general"

    def _path(self, symbol: str) -> Path:
        if not _SYMBOL.fullmatch(symbol or ""):
            raise ValueError("invalid symbol")
        return self.root / f"{symbol}.json"

    def read(self, symbol: str) -> dict | None:
        path = self._path(symbol)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, symbol: str, record: dict) -> None:
        path = self._path(symbol)
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


def _names(text: str, *, symbol: str) -> dict[str, str]:
    out = {}
    for row in json.loads(text).get("data") or []:
        if row.get("code") == symbol and row.get("ratioCode") in CODES and str(row.get("itemName") or "").strip():
            out.setdefault(row["ratioCode"], " ".join(str(row["itemName"]).split()))
    return dict(sorted(out.items()))


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def sync_general_ratios(data_dir: Path, *, get: Callable[[str], str], now: datetime, symbols: list[str] | None = None, limit: int = 60,
                        sleep: Callable[[float], None] = time.sleep, pace: float = 0.5) -> dict:
    store = GeneralRatioStore(data_dir)
    if symbols:
        todo = [s.strip().upper() for s in symbols if _SYMBOL.fullmatch(s.strip().upper())]
        due = len(todo)
    else:
        sectors = _read_json(Path(data_dir) / "industries.json").get("sectors") or {}
        listed = [s for s in (_read_json(Path(data_dir) / "hose-listing.json").get("listing") or {}).get("symbols") or []
                  if _SYMBOL.fullmatch(str(s)) and kind_of(sectors.get(s)) is None]
        ages = []
        for s in listed:
            record = store.read(s)
            when = datetime.fromisoformat(record["fetched_at"]) if record and record.get("fetched_at") else None
            if when is None or now - when >= STALE:
                ages.append((when is not None, when.isoformat() if when else "", s))
        pending = [s for _, _, s in sorted(ages)]
        due, todo = len(pending), pending[:max(0, limit)]
    updated = empty = 0
    failed: dict[str, str] = {}
    for i, symbol in enumerate(todo):
        if i:
            sleep(pace)
        try:
            text = get(URL.format(symbol=symbol, codes=",".join(CODES), start=FIRST_START))
            quarters = parse_ratios(text, symbol=symbol, codes=CODES)
        except Exception as exc:  # noqa: BLE001 - one ticker failing must not stop the run; it is reported
            failed[symbol] = type(exc).__name__
            continue
        if not quarters:
            empty += 1
            continue
        store.save(symbol, {"symbol": symbol, "kind": "general", "fetched_at": now.isoformat(), "source": SOURCE,
                            "names": _names(text, symbol=symbol), "quarters": quarters})
        updated += 1
    return {"status": "partial" if failed else "ok", "due": due, "updated": updated, "empty": empty, "failed": failed}
