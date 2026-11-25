"""Thuyết minh tự động (25/11/2026; docs/superpowers/specs/2026-11-25-thuyet-minh-tu-dong-design.md): the notes to the statements of watched
non-financial companies from Vietcap's public IQ API (the source the owner approved on 08/11/2026 for the banks' notes): borrowings by kind,
financial income and costs by kind, and the year's movement of tangible fixed assets, which VNDirect does not split.

One call per company, 10 seconds before each (robots.txt Crawl-delay; this step follows bank-notes-sync, which also asks Vietcap), under this
application's own name; each company at most weekly and at most fifteen a run, the oldest first (a step is stopped after 10 minutes); a refused
or failed call ends the run, the rest waiting for the next. Only the named lines are kept, in whole đồng as given; a missing figure is left out.
Public figures, no AI. One JSON file per company under data/company-notes.
"""

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from investment_agent.market.financial_ratios import kind_of

URL = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/company/{symbol}/financial-statement?section=NOTE"
SOURCE = "vietcap:iq"
DELAY_SECONDS = 10
MAX_AGE = timedelta(days=7)
LIMIT = 15
# Vietcap's NOTE fields (financial-statement/metrics, checked 25/11/2026) → names
FIELDS = {
    "st_loans_contract": "noc66", "lt_due": "noc67", "lt_bank": "noc94", "lt_other": "noc95", "bonds": "noc96", "finance_lease": "noc97",
    "fin_interest": "noc123", "fin_bond_interest": "noc124", "fin_dividends": "noc125", "fin_disposals": "noc155", "fin_fx_sale": "noc126",
    "fin_fx_realised": "noc127", "fin_fx_unrealised": "noc128", "fin_other": "noc130",
    "exp_interest": "noc132", "exp_disposals": "noc134", "exp_fx_realised": "noc136", "exp_fx_unrealised": "noc137", "exp_provision": "noc138",
    "exp_other": "noc139",
    "ppe_cost_open": "noc36", "ppe_cost_add": "noc37", "ppe_cost_out": "noc38", "ppe_dep_add": "noc41",
    # Chi phí theo yếu tố, hàng tồn kho theo loại (25/11/2026)
    "cost_total": "noc140", "cost_materials": "noc141", "cost_labour": "noc142", "cost_depreciation": "noc143", "cost_services": "noc144",
    "cost_other": "noc145",
    "inv_transit": "noc16", "inv_materials": "noc17", "inv_tools": "noc18", "inv_wip": "noc19", "inv_finished": "noc20", "inv_goods": "noc21",
    "inv_consigned": "noc22", "inv_bonded": "noc23", "inv_property": "noc24",
}
# Raised when FIELDS gains lines: a record kept with an older set is due before its week is out. 2: costs by element, inventory by kind.
FIELDS_VERSION = 2
_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


class CompanyNoteStore:
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
    if value is None:
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return format(d.to_integral_value(ROUND_HALF_UP), "f") if d.is_finite() else None


def parse_company_notes(text: str, *, symbol: str) -> dict:
    """{"years": {year: {name: đồng}}, "quarters": {"2026-Q3": {...}}}; another ticker's rows and missing figures are left out."""
    data = json.loads(text).get("data") or {}
    out = {"years": {}, "quarters": {}}
    for part in ("years", "quarters"):
        for row in data.get(part) or []:
            if str(row.get("ticker", "")).upper() != symbol.upper():
                continue
            try:
                year, length = int(row["yearReport"]), int(row["lengthReport"])
            except (KeyError, TypeError, ValueError):
                continue
            if part == "years" and length != 5 or part == "quarters" and length not in (1, 2, 3, 4):
                continue
            values = {name: v for name, code in FIELDS.items() if (v := _whole(row.get(code))) is not None}
            if values:
                out[part][str(year) if part == "years" else f"{year}-Q{length}"] = values
    return {k: dict(sorted(v.items())) for k, v in out.items()}


def sync_company_notes(store: CompanyNoteStore, sectors: dict[str, str | None], *, get: Callable[[str], str],
                       sleep: Callable[[float], None] = time.sleep, now: datetime | None = None, limit: int = LIMIT) -> dict[str, str]:
    """Refresh the non-financial watched companies a week old or missing, the oldest first, at most `limit`; ok, fresh, later, skipped, error."""
    now = now or datetime.now(timezone.utc)
    results, due = {}, []
    for symbol in sorted(s for s, sector in sectors.items() if kind_of(sector) is None):
        old = store.read(symbol)
        if old and old.get("fields_version", 1) >= FIELDS_VERSION and now - datetime.fromisoformat(old["fetched_at"]) < MAX_AGE:
            results[symbol] = "fresh"
        else:
            due.append((old["fetched_at"] if old else "", symbol))
    refused = False
    for i, (_, symbol) in enumerate(sorted(due)):
        if i >= limit:
            results[symbol] = "later"
            continue
        if refused:  # Vietcap said no: ask nothing more in this run
            results[symbol] = "skipped"
            continue
        sleep(DELAY_SECONDS)
        try:
            parsed = parse_company_notes(get(URL.format(symbol=symbol)), symbol=symbol)
        except Exception as exc:
            results[symbol] = f"error:{type(exc).__name__}"
            refused = True
            continue
        if not parsed["years"] and not parsed["quarters"]:
            results[symbol] = "error:no_observations"
            continue
        store.save({"symbol": symbol, "fetched_at": now.isoformat(), "source": SOURCE, "fields_version": FIELDS_VERSION, **parsed})
        results[symbol] = "ok"
    return dict(sorted(results.items()))
