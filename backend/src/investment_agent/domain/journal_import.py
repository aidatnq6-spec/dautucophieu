"""Bringing an older investment journal into Nhật ký: the Excel 2003 XML that the owner's old HTML journal exports, or a CSV with the
same columns. Nothing is guessed: a line with an impossible date, an unreadable number or an unknown order is reported with its line
number and left out (the old page wrote today's date instead). Imported entries carry no market context, because none was recorded,
and never touch the ledger: the old file has no fees or taxes, and its profit and loss was typed by hand.

Each line's entry id comes from its content, so importing the same file twice adds nothing; identical lines count separately.
"""

import csv
import hashlib
import io
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .bank_figures import _fold
from .journal import JournalEntry

_SS = "{urn:schemas-microsoft-com:office:spreadsheet}"
_SYMBOL = re.compile(r"^[A-Z0-9]{2,10}$")
_COLUMNS = {"asset": ("loai tai san",), "date": ("ngay giao dich", "ngay"), "side": ("lenh",), "ticker": ("ma",), "qty": ("sl tong", "so luong"),
            "price": ("gia von",), "total": ("gia tri von",), "pnl": ("lai/lo",), "reason": ("ly do",)}
_NEEDED = ("date", "side", "ticker")
# Assets other than shares may name anything ("Đất Long An"): the entry needs a code, the name is kept with it.
_STAND_IN = {"bat dong san": "BDS", "bitcoin": "BTC", "tien gui": "TIENGUI", "trai phieu": "TRAIPHIEU", "vang": "VANG", "khac": "KHAC"}
_KIND = {"mua": "buy", "ban": "sell", "dang giu": "hold"}


class ImportFileError(ValueError):
    pass


def _xml_rows(text: str) -> list[tuple[int, list[tuple[str, str]]]]:
    if re.search(r"<!(DOCTYPE|ENTITY)", text, re.I):
        raise ImportFileError("File có khai báo không được phép.")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ImportFileError("Không đọc được file Excel này.") from exc
    rows = []
    for number, row in enumerate(root.iter(f"{_SS}Row"), start=1):
        cells: list[tuple[str, str]] = []
        for cell in row.findall(f"{_SS}Cell"):
            if index := cell.get(f"{_SS}Index"):
                cells.extend(("String", "") for _ in range(int(index) - 1 - len(cells)))
            data = cell.find(f"{_SS}Data")
            cells.append(("" if data is None else data.get(f"{_SS}Type", "String"), "" if data is None or data.text is None else data.text.strip()))
        rows.append((number, cells))
    return rows


def _csv_rows(text: str) -> list[tuple[int, list[tuple[str, str]]]]:
    first = text.split("\n", 1)[0]
    delimiter = ";" if first.count(";") > first.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return [(reader.line_num, [("Text", c.strip()) for c in row]) for row in reader]


def _number(kind: str, raw: str) -> Decimal | None:
    """A plain number from an Excel cell; a Vietnamese one (1.000 or 20.000,5) from text. None when blank; ValueError when unreadable."""
    t = raw.strip()
    if not t:
        return None
    if kind != "Number":
        negative = t.startswith("-") or (t.startswith("(") and t.endswith(")"))
        t = t.strip("()-")
        if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", t):
            t = t.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"\d+(,\d+)?", t):
            t = t.replace(",", ".")
        elif not re.fullmatch(r"\d+\.\d+", t):
            raise ValueError(raw)
        t = ("-" if negative else "") + t
    try:
        value = Decimal(t)
    except InvalidOperation as exc:
        raise ValueError(raw) from exc
    if not value.is_finite():
        raise ValueError(raw)
    return value


def _plain(d: Decimal | None) -> str | None:
    return None if d is None else format(d.normalize(), "f")


def _date(raw: str) -> date:
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", raw)
    return date(int(m[3]), int(m[2]), int(m[1])) if m else datetime.strptime(raw, "%Y-%m-%d").date()


def parse_journal_file(text: str, *, today: date) -> tuple[list[JournalEntry], list[dict]]:
    """(entries, problems): every readable line as an entry, and {line, message} for each one left out."""
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise ImportFileError("File trống.")
    rows = _xml_rows(text) if text.lstrip().startswith("<") else _csv_rows(text)
    rows = [(n, cells) for n, cells in rows if any(v for _, v in cells)]
    if not rows:
        raise ImportFileError("File trống.")
    header = [_fold(v).strip() for _, v in rows[0][1]]
    where = {key: next((i for i, h in enumerate(header) if any(h == a or (a != "ma" and h.startswith(a)) for a in names)), None)
             for key, names in _COLUMNS.items()}
    if lacking := [k for k in _NEEDED if where[k] is None]:
        raise ImportFileError(f"Thiếu cột bắt buộc ({', '.join(lacking)}): cần Ngày giao dịch, Lệnh, Mã.")
    entries, problems, seen = [], [], {}
    for line, cells in rows[1:]:
        def cell(key: str) -> tuple[str, str]:
            i = where[key]
            return cells[i] if i is not None and i < len(cells) else ("String", "")
        if any(_fold(v).startswith("tong cong") for _, v in cells):  # the old export's totals row
            continue
        def bad(message: str) -> None:
            problems.append({"line": line, "message": message})
        raw_date = cell("date")[1]
        try:
            when = _date(raw_date)
        except (ValueError, TypeError):
            bad(f"Ngày không hợp lệ: {raw_date or '(trống)'}")
            continue
        if when > today:
            bad(f"Ngày ở tương lai: {raw_date}")
            continue
        kind = _KIND.get(_fold(cell("side")[1]).strip())
        if kind is None:
            bad(f"Lệnh không rõ: {cell('side')[1] or '(trống)'} (cần Mua hoặc Bán)")
            continue
        try:
            qty, price, total, pnl = (_number(*cell(k)) for k in ("qty", "price", "total", "pnl"))
        except ValueError as exc:
            bad(f"Số không đọc được: {exc}")
            continue
        if not total and qty and price:
            total = qty * price
        if not total and kind != "hold":
            bad("Thiếu giá trị vốn hoặc (giá vốn và số lượng)")
            continue
        asset, ticker = cell("asset")[1] or "Cổ phiếu", cell("ticker")[1]
        symbol = ticker.upper()
        if not _SYMBOL.fullmatch(symbol):
            symbol = _STAND_IN.get(_fold(asset).strip(), "")
            if not symbol:
                bad(f"Mã không hợp lệ: {ticker or '(trống)'}")
                continue
        reason = cell("reason")[1]
        if len(reason) > 4000:
            bad("Lý do dài quá 4.000 ký tự")
            continue
        imported = {"asset": asset, "ticker": ticker, "qty": _plain(qty), "price": _plain(price), "total": _plain(total),
                    "pnl": _plain(pnl) if kind == "sell" else None}
        content = "|".join(str(x) for x in (when, kind, symbol, *imported.values(), reason))
        seen[content] = seen.get(content, 0) + 1
        entry_id = "imp-" + hashlib.sha256(f"{content}|{seen[content]}".encode()).hexdigest()[:40]
        entries.append(JournalEntry(entry_id=entry_id, symbol=symbol, kind=kind, created_on=when, reason=reason, imported=imported))
    return entries, problems
