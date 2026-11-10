"""Thu chi hằng tháng: the monthly totals from the owner's spending workbook, read from its 'Tổng' sheet by column name, never by cell position.
Only totals per month and per source are read; the lines of spending, names and notes on the month sheets are not. A month whose formulas Excel has
not worked out is named and left out, never guessed. Personal data; never sent to a model."""

import io
import re
import zipfile
import xml.etree.ElementTree as ET
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MAX_PART = 40 * 1024 * 1024  # uncompressed size allowed for any one part read
PASSIVE = ("cho thuê", "tiền gửi", "trái phiếu", "chứng chỉ quỹ")  # paid regularly; gains on gold, stocks or property are one-offs
_MISSING = object()


class CashflowFileError(ValueError):
    """Why the file cannot be read, in the owner's language."""


def _norm(text: str) -> str:
    return " ".join(text.split())


def _read(z: zipfile.ZipFile, name: str) -> ET.Element:
    info = z.getinfo(name)
    if info.file_size > MAX_PART:
        raise CashflowFileError("File quá lớn để đọc.")
    return ET.fromstring(z.read(info))


def _cells(z: zipfile.ZipFile) -> dict[tuple[int, int], object]:
    try:
        shared = [_norm("".join(t.text or "" for t in si.iter(f"{M}t"))) for si in _read(z, "xl/sharedStrings.xml").findall(f"{M}si")]
    except KeyError:
        shared = []
    rels = {r.get("Id"): r.get("Target") for r in _read(z, "xl/_rels/workbook.xml.rels")}
    sheet = next((s for s in _read(z, "xl/workbook.xml").iter(f"{M}sheet") if _norm(s.get("name", "")).casefold() == "tổng"), None)
    if sheet is None:
        raise CashflowFileError("Không thấy trang “Tổng” trong file.")
    target = rels[sheet.get(f"{R}id")].lstrip("/")
    out: dict[tuple[int, int], object] = {}
    for c in _read(z, target if target.startswith("xl/") else "xl/" + target).iter(f"{M}c"):
        m = re.fullmatch(r"([A-Z]+)(\d+)", c.get("r") or "")
        if not m:
            continue
        col = 0
        for ch in m.group(1):
            col = col * 26 + ord(ch) - 64
        v, f, inline = c.find(f"{M}v"), c.find(f"{M}f"), c.find(f"{M}is")
        if inline is not None:
            value: object = _norm("".join(t.text or "" for t in inline.iter(f"{M}t")))
        elif v is None:
            value = _MISSING if f is not None else None
        elif c.get("t") == "s":
            value = shared[int(v.text)]
        elif c.get("t") in ("str", "e", "b"):
            value = v.text or ""
        else:
            try:
                value = Decimal(v.text)
            except (InvalidOperation, TypeError):
                value = v.text
        if value is not None and value != "":
            out[(int(m.group(2)), col)] = value
    return out


def parse_cashflow_xlsx(data: bytes) -> dict:
    """{"year", "months": {"YYYY-MM": {"income", "spending", "sources": {label: amount}}}, "sources": [{"label", "group", "passive"}], "warnings"}."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            cells = _cells(z)
    except CashflowFileError:
        raise
    except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError, ValueError):
        raise CashflowFileError("Không đọc được file: cần file Excel .xlsx thu chi hằng tháng.") from None
    texts = {k: v for k, v in cells.items() if isinstance(v, str)}
    header = next(((r, c) for (r, c), t in sorted(texts.items()) if t.casefold() == "tháng" and sum(1 for (r2, c2) in texts if r2 == r and c2 > c) >= 2), None)
    if header is None:
        raise CashflowFileError("Trang “Tổng” thiếu dòng tiêu đề bắt đầu bằng cột “Tháng”.")
    hrow, mcol = header
    labels = {c: t for (r, c), t in texts.items() if r == hrow and c > mcol}
    income = next((c for c, t in labels.items() if t.casefold().startswith("tổng thu nhập")), None)
    spending = next((c for c, t in labels.items() if t.casefold() == "tổng chi"), None)
    if income is None or spending is None:
        raise CashflowFileError("Trang “Tổng” thiếu cột “Tổng Thu nhập…” hoặc “Tổng Chi”.")
    year_at = next(((r, c) for (r, c), t in texts.items() if t.casefold() == "năm hiện tại"), None)
    year = cells.get((year_at[0], year_at[1] + 1)) if year_at else None
    if not isinstance(year, Decimal) or year != year.to_integral_value() or not 2000 <= year <= 2100:
        raise CashflowFileError("Không thấy năm ở ô cạnh “Năm hiện tại” trên trang “Tổng”.")
    groups = sorted((c, t) for (r, c), t in texts.items() if r == hrow - 1 and c > mcol)
    sources = []
    for c, label in sorted(labels.items()):
        if label.casefold().startswith("tổng") or "%" in label:
            continue
        above = [t for gc, t in groups if gc <= c]
        group = above[-1].casefold() if above else ""
        sources.append({"col": c, "label": label, "group": "business" if "kinh doanh" in group else "portfolio" if "danh mục" in group else None,
                        "passive": any(word in label.casefold() for word in PASSIVE)})
    months, warnings = {}, []
    for (r, c), m in sorted(cells.items()):
        if c != mcol or r <= hrow or not isinstance(m, Decimal) or m != m.to_integral_value() or not 1 <= m <= 12:
            continue
        name, key = f"Tháng {int(m)}", f"{int(year):04d}-{int(m):02d}"
        row = {col: cells.get((r, col)) for col in (income, spending, *(s["col"] for s in sources))}
        if row[income] is None and row[spending] is None:
            continue  # not entered yet
        if any(v is _MISSING for v in row.values()):
            warnings.append(f"{name}: có ô công thức chưa được Excel tính; mở file trong Excel, để Excel tính xong rồi lưu lại. Chưa đọc tháng này.")
            continue
        if not isinstance(row[income], Decimal) or not isinstance(row[spending], Decimal) or any(v is not None and not isinstance(v, Decimal) for v in row.values()):
            warnings.append(f"{name}: có ô không phải số. Chưa đọc tháng này.")
            continue
        whole = lambda v: format((v or Decimal(0)).quantize(Decimal(1), ROUND_HALF_UP), "f")  # noqa: E731  a blank source is nothing that month
        months[key] = {"income": whole(row[income]), "spending": whole(row[spending]), "sources": {s["label"]: whole(row[s["col"]]) for s in sources}}
    if not months and not warnings:
        raise CashflowFileError("Trang “Tổng” chưa có tháng nào có số thu chi.")
    return {"year": int(year), "months": months, "sources": [{k: s[k] for k in ("label", "group", "passive")} for s in sources], "warnings": warnings}
