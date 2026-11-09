"""Reading a TCInvest "Lịch sử giao dịch cổ phiếu" export (.xlsx) into matched orders for Sổ giao dịch. The file is read as data, with the
standard library only; a line that cannot be read exactly is reported with its row number and left out, never completed by guesswork."""

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .bank_figures import _fold

_N = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
MAX_XML_BYTES = 20_000_000
_COLUMNS = {"symbol": "ma cp", "date": "ngay gd", "side": "giao dich", "quantity": "kl khop", "price": "gia khop", "fee": "phi", "tax": "thue", "status": "trang thai", "order_no": "so hieu lenh"}
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
_SIDE = {"mua": "buy", "ban": "sell"}


class StatementFileError(ValueError):
    pass


def _xml(z: zipfile.ZipFile, name: str) -> ET.Element:
    raw = z.read(name)
    if re.search(rb"<!(DOCTYPE|ENTITY)", raw, re.I):
        raise StatementFileError("File có khai báo không được phép.")
    return ET.fromstring(raw)


def _rows(data: bytes) -> list[tuple[int, dict[str, str]]]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_XML_BYTES:
                raise StatementFileError("File quá lớn.")
            sheets = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))
            if not sheets:
                raise StatementFileError("Không thấy bảng tính trong file.")
            shared = ["".join(t.text or "" for t in si.iter(f"{_N}t")) for si in _xml(z, "xl/sharedStrings.xml").findall(f"{_N}si")] if "xl/sharedStrings.xml" in z.namelist() else []
            sheet = _xml(z, sheets[0])
    except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError) as exc:
        raise StatementFileError("Không đọc được file Excel này.") from exc
    out = []
    for row in sheet.iter(f"{_N}row"):
        cells = {}
        for c in row.findall(f"{_N}c"):
            kind, v = c.get("t", "n"), c.find(f"{_N}v")
            if kind == "inlineStr":
                text = "".join(t.text or "" for t in c.iter(f"{_N}t"))
            elif v is None or v.text is None:
                text = ""
            else:
                text = shared[int(v.text)] if kind == "s" else v.text
            cells[re.sub(r"\d", "", c.get("r", ""))] = text.strip()
        out.append((int(row.get("r", len(out) + 1)), cells))
    return out


def _amount(raw: str) -> Decimal:
    value = Decimal(raw)
    if not value.is_finite() or value < 0:
        raise InvalidOperation
    return value


def _plain(d: Decimal) -> str:
    return format(d.normalize(), "f")


def parse_tcbs_xlsx(data: bytes, *, today: date) -> tuple[list[dict], list[dict]]:
    """(orders, problems): {line, symbol, type, date, quantity, price, fee, tax, order_no} for each matched order, {line, message} for each left out."""
    rows = _rows(data)
    head = next((i for i, (_, cells) in enumerate(rows) if any(_fold(v).startswith("ma cp") for v in cells.values())), None)
    if head is None:
        raise StatementFileError("Thiếu các cột của sao kê TCBS (không thấy cột Mã CP).")
    titles = {col: _fold(v.split("\n")[0]).strip() for col, v in rows[head][1].items()}
    where = {key: next((c for c, t in titles.items() if t == name or t.startswith(name + " ")), None) for key, name in _COLUMNS.items()}
    if lacking := [_COLUMNS[k] for k, c in where.items() if c is None]:
        raise StatementFileError(f"Thiếu cột của sao kê TCBS: {', '.join(lacking)}.")
    orders, problems = [], []
    for number, cells in rows[head + 1:]:
        get = lambda key: cells.get(where[key], "")  # noqa: E731
        symbol, raw_day = get("symbol").upper(), get("date")
        if not _SYMBOL.fullmatch(symbol) or (not raw_day and not get("side")):  # a totals row or the footnote
            continue

        def bad(message: str) -> None:
            problems.append({"line": number, "message": f"{symbol}: {message}"})
        try:
            when = datetime.strptime(raw_day, "%d/%m/%Y").date()
        except ValueError:
            bad(f"ngày không hợp lệ: {raw_day or '(trống)'}")
            continue
        if when > today:
            bad(f"ngày ở tương lai: {raw_day}")
            continue
        side = _SIDE.get(_fold(get("side")).strip())
        if side is None:
            bad(f"loại giao dịch không rõ: {get('side') or '(trống)'}")
            continue
        if _fold(get("status")).strip() != "hoan tat":
            bad(f"lệnh chưa hoàn tất: {get('status') or '(trống)'}")
            continue
        order_no = get("order_no")
        if not re.fullmatch(r"[A-Za-z0-9]{1,64}", order_no):
            bad("thiếu số hiệu lệnh")
            continue
        fields = {}
        try:
            for key, label in (("quantity", "KL khớp"), ("price", "Giá khớp"), ("fee", "Phí"), ("tax", "Thuế")):
                current = label
                fields[key] = _amount(get(key))
        except InvalidOperation:
            bad(f"{current} không đọc được: {get(key) or '(trống)'}")
            continue
        if fields["quantity"] <= 0 or fields["quantity"] != fields["quantity"].to_integral_value() or fields["price"] <= 0:
            bad("khối lượng hoặc giá khớp không hợp lệ")
            continue
        orders.append({"line": number, "symbol": symbol, "type": side, "date": when, "quantity": int(fields["quantity"]), "price": _plain(fields["price"]),
                       "fee": _plain(fields["fee"]), "tax": _plain(fields["tax"]), "order_no": order_no})
    return orders, problems
