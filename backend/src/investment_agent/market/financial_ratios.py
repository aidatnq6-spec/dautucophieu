"""Quarterly sector ratios of watched banks, securities firms and insurers from VNDirect's public ratios API (the free
statements carry no non-performing loans, provisions or combined ratio). robots.txt of api-finfo.vndirect.com.vn allows
all user agents (use=reference, checked 31/10/2026). One call per ticker, about two years of quarters; rows for another
ticker or code and non-numeric values are dropped, never repaired. One JSON file per ticker under data/financial-ratios.
"""

import json
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from .leading import _get_with_retry

KINDS = {"Ngân hàng": "bank", "Dịch vụ tài chính": "securities", "Bảo hiểm": "insurance"}
# Shown on the ticker page (Chỉ số ngành theo quý), in this order: code, label, format (pct1/pct2/times). The health score
# (valuation/quality.py) uses a subset.
DISPLAY = {
    "bank": (("BAD_LOANS_RATIO_AQ", "Tỷ lệ nợ xấu (NPL)", "pct2"), ("OVERDUE_LOANS_RATIO_AQ", "Tỷ lệ nợ quá hạn", "pct2"),
             ("PROVISION_BAD_LOANS_AQ", "Bao phủ nợ xấu", "pct0"), ("NET_INTEREST_MARGIN_TR_AVG5Q", "NIM", "pct2"),
             ("LOANS_TO_DEPOSIT_AQ", "Cho vay / tiền gửi (LDR)", "pct1"), ("CUSTOMER_LOANS_AQ_GRYOY", "Tăng trưởng cho vay (so cùng kỳ)", "pct1"),
             ("EQUITY_TO_ASSET_AQ", "Vốn chủ / tổng tài sản", "pct1"), ("ROAA_TR_AVG4Q", "ROAA", "pct2"), ("ROAE_TR_AVG4Q", "ROAE", "pct1")),
    "securities": (("ROAA_TR_AVG4Q", "ROAA", "pct2"), ("ROAE_TR_AVG4Q", "ROAE", "pct1"), ("NET_MARGIN_TR", "Biên lợi nhuận ròng", "pct1"),
                   ("LOANS_TO_EQUITY_AQ", "Cho vay / vốn chủ", "times"), ("EQUITY_TO_ASSET_AQ", "Vốn chủ / tổng tài sản", "pct1")),
    "insurance": (("COMBINED_RATIO_TR", "Tỷ lệ kết hợp", "pct1"), ("NET_MARGIN_TR", "Biên lợi nhuận ròng", "pct1"), ("ROAA_TR_AVG4Q", "ROAA", "pct2"),
                  ("ROAE_TR_AVG4Q", "ROAE", "pct1"), ("EQUITY_TO_ASSET_AQ", "Vốn chủ / tổng tài sản", "pct1")),
}
CODES = {kind: tuple(code for code, _, _ in rows) for kind, rows in DISPLAY.items()}
URL = "https://api-finfo.vndirect.com.vn/v4/ratios?q=code:{symbol}~ratioCode:{codes}~reportDate:gte:{start}&sort=reportDate:desc&size=500"
HISTORY_DAYS = 800  # the latest quarter and the same quarter a year before, with room for a late report
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


def kind_of(sector: str | None) -> str | None:
    return KINDS.get(sector or "")


class FinancialRatioStore:
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


def parse_ratios(text: str, *, symbol: str, codes: tuple[str, ...]) -> dict[str, dict[str, str]]:
    quarters: dict[str, dict[str, str]] = {}
    for row in json.loads(text).get("data") or []:
        if row.get("code") != symbol or row.get("ratioCode") not in codes:
            continue
        try:
            value, day = Decimal(str(row["value"])), date.fromisoformat(row["reportDate"])
        except (InvalidOperation, KeyError, TypeError, ValueError):
            continue
        if value.is_finite():
            quarters.setdefault(day.isoformat(), {})[row["ratioCode"]] = format(value.normalize(), "f")
    return dict(sorted(quarters.items()))


def fetch_financial_ratios(store: FinancialRatioStore, sectors: dict[str, str], *, get: Callable[[str], str], today: date,
                           sleep: Callable[[float], None] = time.sleep) -> dict[str, str]:
    """Refresh every watched financial ticker; one failing is reported and the others still update."""
    results = {}
    for symbol, sector in sorted(sectors.items()):
        kind = kind_of(sector)
        if kind is None:
            continue
        try:
            url = URL.format(symbol=symbol, codes=",".join(CODES[kind]), start=(today - timedelta(days=HISTORY_DAYS)).isoformat())
            quarters = parse_ratios(_get_with_retry(get, url, sleep), symbol=symbol, codes=CODES[kind])
            if not quarters:
                results[symbol] = "error:no_observations"
                continue
            store.save({"symbol": symbol, "kind": kind, "fetched_at": datetime.now(timezone.utc).isoformat(), "source": "vndirect:finfo",
                        "quarters": quarters})
            results[symbol] = "ok"
        except Exception as exc:
            results[symbol] = f"error:{type(exc).__name__}"
    return results
