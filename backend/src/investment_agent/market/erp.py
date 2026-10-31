"""Equity risk premium for Vietnam from Aswath Damodaran's country table (NYU Stern, ctryprem.xlsx, free; robots.txt allows it),
the default for the CAPM hint until the owner enters their own. Read at most once a week by the scheduler; the file's
Last-Modified date is kept as its publication date (the date cell inside the book is not maintained). The workbook is read
with the standard library: columns are found by their header names, and a book without the row keeps the old value.
"""

import io
import json
import os
import re
import zipfile
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree

URL = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/ctryprem.xlsx"
SHEET = "ERPs by country"
COUNTRY = "Vietnam"
MAX_AGE = timedelta(days=7)
_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


class ErpStore:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "erp.json"

    def read(self) -> dict | None:
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else None

    def save(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(tmp, self.path)


def _rows(book: bytes, sheet: str) -> list[dict[str, str]]:
    """One sheet as rows of {column letter: text}."""
    z = zipfile.ZipFile(io.BytesIO(book))
    names = z.namelist()
    strings = ["".join(t.text or "" for t in si.iter(_M + "t")) for si in ElementTree.fromstring(z.read("xl/sharedStrings.xml")).findall(_M + "si")] \
        if "xl/sharedStrings.xml" in names else []
    targets = {r.get("Id"): r.get("Target") for r in ElementTree.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    for s in ElementTree.fromstring(z.read("xl/workbook.xml")).iter(_M + "sheet"):
        if s.get("name") == sheet:
            target = targets[s.get(_REL)].lstrip("/")
            root = ElementTree.fromstring(z.read(target if target.startswith("xl/") else "xl/" + target))
            out = []
            for row in root.iter(_M + "row"):
                cells = {}
                for c in row.findall(_M + "c"):
                    v = c.find(_M + "v")
                    if v is None or v.text is None:
                        continue
                    cells[re.sub(r"\d", "", c.get("r", ""))] = strings[int(v.text)] if c.get("t") == "s" else v.text
                out.append(cells)
            return out
    return []


def _pct(value: str | None) -> str | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None
    return format(d.quantize(Decimal("0.0001"), ROUND_HALF_UP), "f") if d.is_finite() and Decimal(0) < d < 1 else None


def parse_country_erp(book: bytes, country: str = COUNTRY) -> dict | None:
    """Total equity risk premium (rating-based, and CDS-based) and Moody's rating for one country, as ratios rounded to 0.01 point."""
    rows = _rows(book, SHEET)
    header = next((r for r in rows if "Country" in r.values() and "Total Equity Risk Premium" in r.values()), None)
    if header is None:
        return None
    col = {v.strip(): k for k, v in header.items()}
    for r in rows:
        if r.get(col["Country"], "").strip() == country:
            erp = _pct(r.get(col["Total Equity Risk Premium"]))
            if erp is None:
                return None
            cds = col.get("Total Equity Risk Premium2")
            rating = col.get("Moody's rating")
            return {"erp": erp, "erp_cds": _pct(r.get(cds)) if cds else None, "rating": r.get(rating) if rating else None}
    return None


def erp_sync(store: ErpStore, *, get: Callable[[str], tuple[bytes, str | None]], now: datetime, force: bool = False) -> dict:
    saved = store.read()
    if saved and not force and now - datetime.fromisoformat(saved["fetched_at"]) < MAX_AGE:
        return {"status": "fresh", "erp": saved["erp"], "published": saved.get("published")}
    try:
        book, modified = get(URL)
        found = parse_country_erp(book)
    except Exception as exc:
        return {"status": "error", "reason": type(exc).__name__}
    if found is None:
        return {"status": "error", "reason": f"{COUNTRY} not in {SHEET}"}
    published = parsedate_to_datetime(modified).date().isoformat() if modified else None
    store.save({**found, "published": published, "fetched_at": now.isoformat(), "source": URL})
    return {"status": "ok", "erp": found["erp"], "published": published}
