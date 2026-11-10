"""Số liệu ngân hàng nhập tay: loans by group 1–5, customer deposits and CAR per quarter, and the ratios the owner's
spreadsheet computes from them. No free source publishes these (checked 31/10/2026), so the owner enters them from the
notes to the quarterly statements, or has them read from a public PDF and confirms before saving.

The PDF reader only proposes values: each comes with its page, amounts are converted to tỷ đồng only when the page (or
an earlier one) states its unit, and a label not found is reported missing, never filled in. Labels are matched without
accents, so a scanned page read by OCR ("Nợ cân chú ý", "mắt vốn") still matches; a figure read from such a page must also
add up to the total printed with it where there is one, or it is left blank with both numbers shown.
"""

import ipaddress
import re
import socket
import unicodedata
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Callable
from urllib.parse import urlsplit

GROUPS = ("group1", "group2", "group3", "group4", "group5")
CORE = (*GROUPS, "demand_deposits", "margin_deposits", "customer_deposits", "car")
# Chất lượng tài sản (10/11/2026): provisions and accrued interest are read from the balance sheet; property loans and discounted documents by hand.
QUALITY = ("reserve", "accrued_interest", "real_estate_loans", "discounted_documents")
FIELDS = (*CORE, *QUALITY)
LABELS = {"reserve": "Dự phòng rủi ro cho vay khách hàng (số dư)", "accrued_interest": "Lãi và phí phải thu", "real_estate_loans": "Dư nợ kinh doanh bất động sản",
          "discounted_documents": "Chiết khấu bộ chứng từ, phải thu ngoài cho vay", "group1": "Nợ nhóm 1 (đủ tiêu chuẩn)", "group2": "Nợ nhóm 2 (cần chú ý)", "group3": "Nợ nhóm 3 (dưới tiêu chuẩn)",
          "group4": "Nợ nhóm 4 (nghi ngờ)", "group5": "Nợ nhóm 5 (có khả năng mất vốn)", "demand_deposits": "Tiền gửi không kỳ hạn",
          "margin_deposits": "Tiền gửi ký quỹ", "customer_deposits": "Tiền gửi của khách hàng", "car": "CAR (%)"}
_Q4 = Decimal("0.0001")


def _d(value) -> Decimal | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return d if d.is_finite() else None


def _ratio(top: Decimal | None, bottom: Decimal | None) -> str | None:
    return str((top / bottom).quantize(_Q4, ROUND_HALF_UP)) if top is not None and bottom else None


def derive(q: dict) -> dict:
    """NPL = groups 3–5 over groups 1–5; group-2 share; CASA = (demand + margin deposits) / customer deposits; CAR as a ratio."""
    groups = [_d(q.get(g)) for g in GROUPS]
    total = sum(groups) if None not in groups else None
    bad = groups[2] + groups[3] + groups[4] if None not in groups[2:] else None
    demand, margin = _d(q.get("demand_deposits")), _d(q.get("margin_deposits"))
    car = _d(q.get("car"))
    return {"npl": _ratio(bad, total) if total else None, "group2_ratio": _ratio(groups[1], total) if total else None,
            "casa": _ratio(demand + margin, _d(q.get("customer_deposits"))) if demand is not None and margin is not None else None,
            "car": str((car / 100).quantize(_Q4, ROUND_HALF_UP)) if car is not None else None,
            "llr": _ratio(_d(q.get("reserve")), bad) if bad else None,  # tỷ lệ bao phủ nợ xấu: provisions over groups 3–5
            "real_estate_share": _ratio(_d(q.get("real_estate_loans")), total) if total else None}


# The application's own lines for a sign worth a closer look, stated on the page; not research cut-offs and not a finding.
LLR_DROP, GROUP2_JUMP, ACCRUED_JUMP, DOCUMENTS_JUMP, REAL_ESTATE_PACE = Decimal("0.10"), Decimal("0.30"), Decimal("0.20"), Decimal("0.30"), Decimal("1.5")


def _quarter_before(key: str, back: int) -> str:
    y, n = int(key[:4]), int(key[-1]) - back
    while n < 1:
        y, n = y - 1, n + 4
    return f"{y}-Q{n}"


def quality_trend(quarters: dict[str, dict]) -> dict[str, dict]:
    """Per quarter: cover against the quarter before, the same quarter a year before and the end of last year; growth of group 2, loans, accrued
    interest, discounted documents and property loans; and the warning signs. A comparison missing a figure is None, never guessed."""
    def num(values: dict | None, field: str) -> Decimal | None:
        return _d(values.get(field)) if values else None

    def total(values: dict | None) -> Decimal | None:
        groups = [num(values, g) for g in GROUPS]
        return sum(groups) if values and None not in groups else None

    def bad(values: dict | None) -> Decimal | None:
        groups = [num(values, g) for g in GROUPS[2:]]
        return sum(groups) if values and None not in groups else None

    def growth(new: Decimal | None, old: Decimal | None) -> Decimal | None:
        return new / old - 1 if new is not None and old else None

    def s(v: Decimal | None) -> str | None:
        return str(v.quantize(_Q4, ROUND_HALF_UP)) if v is not None else None

    out = {}
    for key in sorted(quarters):
        cur, prev = quarters[key], quarters.get(_quarter_before(key, 1))
        year_ago, start = quarters.get(_quarter_before(key, 4)), quarters.get(f"{int(key[:4]) - 1}-Q4")
        llr = {name: _d(derive(v)["llr"]) if v else None for name, v in (("cur", cur), ("prev", prev), ("year_ago", year_ago), ("start", start))}
        g2 = growth(num(cur, "group2"), num(prev, "group2"))
        loans_q, loans_y = growth(total(cur), total(prev)), growth(total(cur), total(start))
        accrued, docs = growth(num(cur, "accrued_interest"), num(prev, "accrued_interest")), growth(num(cur, "discounted_documents"), num(prev, "discounted_documents"))
        real_estate = growth(num(cur, "real_estate_loans"), num(start, "real_estate_loans"))
        reserve_now, reserve_before = num(cur, "reserve"), num(prev, "reserve")
        flags = []
        if llr["cur"] is not None and any(llr[k] is not None and llr[k] - llr["cur"] >= LLR_DROP for k in ("prev", "start")):
            flags.append("llr_falling")
        if g2 is not None and g2 >= GROUP2_JUMP:
            flags.append("group2_jump")
        if None not in (bad(cur), bad(prev), reserve_now, reserve_before) and bad(cur) > bad(prev) and reserve_now < reserve_before:
            flags.append("reserve_lagging")
        if None not in (num(cur, "group5"), num(prev, "group5"), reserve_now, reserve_before) and num(cur, "group5") < num(prev, "group5") and reserve_now < reserve_before:
            flags.append("write_off")
        if accrued is not None and accrued >= ACCRUED_JUMP:
            flags.append("accrued_jump")
        if real_estate is not None and loans_y is not None and real_estate >= Decimal("0.10") and real_estate >= REAL_ESTATE_PACE * max(loans_y, Decimal(0)):
            flags.append("real_estate_fast")
        if docs is not None and docs >= DOCUMENTS_JUMP:
            flags.append("documents_jump")
        out[key] = {"llr": s(llr["cur"]), "llr_prev": s(llr["prev"]), "llr_year_ago": s(llr["year_ago"]), "llr_start": s(llr["start"]),
                    "group2_growth_qoq": s(g2), "loans_growth_qoq": s(loans_q), "loans_growth_ytd": s(loans_y), "accrued_growth_qoq": s(accrued),
                    "documents_growth_qoq": s(docs), "real_estate_growth_ytd": s(real_estate), "flags": flags}
    return out


# ---- reading a public PDF of the quarterly statements -------------------------------------------------------------

_NUMBER = re.compile(r"\(?-?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?\)?|\(?-?\d+(?:[.,]\d+)?\)?%?")
# "Đơn vị: triệu đồng", or a column-header line holding only the unit (and %), e.g. "triệu đồng % triệu đồng %" (Techcombank).
# OCR may merge it with the "Thuyết minh" column ("minh triệu đồng") or read đồng as "đông".
_HEADER = r"^[ \t]*(?:(?:thuyết[ \t]+)?minh[ \t]+)?(?:{u}(?:[ \t]+%)?[ \t]*)+$"
_UNITS = ((re.compile(r"đơn vị[^\n]{0,20}?triệu|" + _HEADER.format(u=r"triệu (?:đồng|đông|vnd)"), re.I | re.M), Decimal(1000)),
          (re.compile(r"đơn vị[^\n]{0,20}?tỷ|" + _HEADER.format(u=r"tỷ (?:đồng|đông|vnd)"), re.I | re.M), Decimal(1)),
          (re.compile(r"đơn vị[^\n]{0,20}?(?:đồng|vnd)", re.I), Decimal(1_000_000_000)))
# The customer-deposit note runs from its numbered heading ("18. TIỀN GỬI CỦA KHÁCH HÀNG") to the next numbered note.
_DEPOSIT_NOTE = re.compile(r"^\s*\d{1,2}\.?\s+tien gui cua khach hang\s*$")  # matched on accent-free text, as all labels
_NEXT_NOTE = re.compile(r"^\s*\d{1,2}\.\s+\S")
# The customer-loan quality section ("9.1 Phân tích chất lượng nợ cho vay"); an interbank-credit quality table with the same
# group labels can sit above it on the same page. Ends at the next sub-heading ("9.2 …") or a line starting with a total.
_LOAN_NOTE = re.compile(r"(?:chat luong|phan loai)\s+no\s+cho vay(?!.*ky quy)")
_SUB_HEADING = re.compile(r"^\s*\d+(?:\.\d+)+\s+\S|^\s*\d{1,2}\.\s+\S")
# A capital-adequacy report: "G Tỷ lệ an toàn vốn 12.45  14.95 …" under a "Riêng lẻ Hợp nhất" header (consolidated second).
_CAR_ROW = re.compile(r"ty le an toan von(?: hop nhat)?\s+(\d{1,2}[.,]\d+)\s+(\d{1,2}[.,]\d+)")
# A total under a table: a line of amounts only, the first written with thousands separators (not a date like 30/09/2026).
_TOTAL_LINE = re.compile(r"^[\s\-.:|]*\(?\d{1,3}(?:[.,]\d{3})+[^a-z]*$")
_SUB_LINE = r"bang (?:vnd|ngoai te)"  # "- Tiền gửi ký quỹ bằng VND": a part of the line above, never its total


def _fold(text: str) -> str:
    """Lower case without accents (đ as d): what a label is matched on, so OCR's slipped accents do not hide it."""
    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").lower()


def _car(text: str) -> str | None:
    """CAR in %, from "… an toàn vốn … 11,50%" or from a separate/consolidated table row; 3–60% or nothing."""
    text = _fold(text)
    m = re.search(r"an toan von[^\n%]*?(\d{1,2}(?:[.,]\d+)?)\s*%", text)
    value = _to_decimal(m.group(1)) if m else None
    if value is None and (row := _CAR_ROW.search(text)):
        value = _to_decimal(row.group(2) if re.search(r"rieng le\s+hop nhat", text) else row.group(1))
    return _plain(value) if value is not None and Decimal(3) <= value <= Decimal(60) else None
_LINE_LABELS = {"group1": r"no du tieu chuan", "group2": r"no can chu y", "group3": r"no duoi tieu chuan", "group4": r"no nghi ngo",
                "group5": r"no co kha nang mat von", "demand_deposits": r"tien gui khong ky han", "margin_deposits": r"tien (?:gui )?ky quy",
                "customer_deposits": r"(?:^|\s)tien gui cua khach hang", "reserve": r"du phong rui ro cho vay khach hang",
                "accrued_interest": r"cac khoan lai,? (?:va )?phi phai thu"}
IMAGE_ONLY = "Không đọc được chữ trong file (có thể là bản scan dạng ảnh); hãy nhập tay."


def _to_decimal(token: str) -> Decimal | None:
    t = token.strip("()%")
    neg = token.startswith("(") or t.startswith("-")
    t = t.lstrip("-")
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", t):  # 447.734.000 or 1.234,5 (Vietnamese)
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", t):  # 447,734,000 or 1,234.5
        t = t.replace(",", "")
    else:
        t = t.replace(",", ".")
    d = _d(t)
    return -d if d is not None and neg else d


def _amount_after(line: str, label: str) -> Decimal | None:
    """First amount after the label, skipping a note number (1–3 digits, no separators) placed before the amounts."""
    line = _fold(line)
    m = re.search(label, line)
    if not m or (label in (_LINE_LABELS["demand_deposits"], _LINE_LABELS["margin_deposits"]) and re.search(_SUB_LINE, line)):
        return None
    for token in _NUMBER.findall(line[m.end():]):
        if token.endswith("%"):
            return None
        if re.fullmatch(r"\d{1,3}", token):
            continue
        return _to_decimal(token)
    return None


def _plain(d: Decimal) -> str:
    return format(d.normalize(), "f")


def _printed(d: Decimal) -> str:
    """An amount as the report prints it: 1.288.128.443 (or 7.230,5)."""
    whole, _, frac = format(abs(d).normalize(), "f").partition(".")
    return ("-" if d < 0 else "") + f"{int(whole):,}".replace(",", ".") + (f",{frac}" if frac else "")


def _total_after(part: list[tuple[int, str]], start: int, within: int = 3) -> Decimal | None:
    """The total printed in the next few lines of a section after position `start`, if one is there."""
    for _, ln in part[start + 1:start + 1 + within]:
        if _TOTAL_LINE.match(_fold(ln)):
            return _to_decimal(_NUMBER.findall(ln)[0])
    return None


def parse_report_pages(pages: list[str], *, ocr: frozenset[int] = frozenset()) -> dict:
    """Proposed values {field: {value (tỷ đồng, CAR in %), page (1-based), ocr when read from an image}}, the fields not
    found, and warnings. `ocr` holds the 0-based pages whose text came from OCR: their figures are checked against totals."""
    if not any(p.strip() for p in pages):
        return {"fields": {}, "missing": list(CORE), "warnings": [IMAGE_ONLY]}
    # PDFs may store Vietnamese letters decomposed (y + ̉ for ỷ); Tesseract on Windows ends lines with \r\n, where "$" fails.
    pages = [unicodedata.normalize("NFC", p).replace("\r\n", "\n").replace("\r", "\n") for p in pages]
    fields, warnings, unit = {}, [], None
    units = []
    for text in pages:
        unit = next((u for pattern, u in _UNITS if pattern.search(text)), unit)  # a page without a unit line inherits the last one
        units.append(unit)
    lines = [[ln for ln in p.splitlines()] for p in pages]

    def section(start: re.Pattern, end: re.Pattern) -> list[tuple[int, str]]:
        """Every (page, line) from a heading to the next heading: other tables share the labels, and even the page."""
        inside, out = False, []
        for i, page_lines in enumerate(lines):
            for ln in page_lines:
                if start.search(folded := _fold(ln)) and not _NUMBER.search(start.split(folded)[-1]):
                    inside = True
                elif inside and end.match(ln) and not _TOTAL_LINE.match(folded):  # "1.288.128.443 …" is a total, not "9.2 …"
                    inside = False
                elif inside:
                    out.append((i, ln))
        return out
    note_lines = section(_DEPOSIT_NOTE, _NEXT_NOTE)
    loan_lines = section(_LOAN_NOTE, _SUB_HEADING)
    unitless = False
    raw: dict[str, tuple[Decimal, Decimal, int]] = {}  # field → (amount as printed, its unit, position in its section)

    def take(field: str, page_indexes, only: list[str] | None = None, at: int = -1) -> None:
        nonlocal unitless
        for i in page_indexes:
            for ln in (lines[i] if only is None else only):
                amount = _amount_after(ln, _LINE_LABELS[field])
                if amount is None:
                    continue
                if units[i] is None:
                    unitless = True
                    return
                fields[field] = {"value": _plain(amount / units[i]), "page": i + 1}
                raw[field] = (amount, units[i], at)
                return

    everywhere = range(len(pages))
    for f, part in ((g, loan_lines) for g in GROUPS):  # loan groups only from the loan-quality section
        for k, (i, ln) in enumerate(part):
            if f not in fields:
                take(f, [i], only=[ln], at=k)
    for f in ("demand_deposits", "margin_deposits"):  # only from the customer-deposit note
        for k, (i, ln) in enumerate(note_lines):
            if f not in fields:
                take(f, [i], only=[ln], at=k)
    take("customer_deposits", everywhere)
    for f in ("reserve", "accrued_interest"):  # balance-sheet lines; a provision is printed in brackets
        take(f, everywhere)
        if f in fields:
            fields[f]["value"] = _plain(abs(Decimal(fields[f]["value"])))
    for i, text in enumerate(pages):
        if car := _car(text):
            fields["car"] = {"value": car, "page": i + 1}
            break
    if ocr:
        warnings.extend(_check_ocr(fields, raw, loan_lines, note_lines, ocr))
    if unitless:
        warnings.append("Không thấy dòng đơn vị (triệu/tỷ đồng) trên trang có số; không điền để tránh sai đơn vị.")
    if not loan_lines:
        warnings.append('Không thấy mục "chất lượng nợ cho vay" (phân loại nợ nhóm 1–5).')
    if not note_lines:
        warnings.append('Không thấy mục thuyết minh có đánh số "Tiền gửi của khách hàng".')
    return {"fields": fields, "missing": [f for f in CORE if f not in fields], "warnings": warnings}


def _check_ocr(fields: dict, raw: dict, loan_lines: list, note_lines: list, ocr: frozenset[int]) -> list[str]:
    """Figures read from an image page must add up to the total printed with them; a miss empties them, and says so."""
    from_image = {f for f, x in fields.items() if x["page"] - 1 in ocr}
    notes, unchecked = [], []

    def drop(names, why: str) -> None:
        for name in names:
            fields.pop(name, None)
        notes.append(why + " OCR đọc sai ít nhất một chữ số nên để trống, hãy nhập tay từ file.")

    if from_image & set(GROUPS):
        total = _total_after(loan_lines, raw["group5"][2]) if all(g in raw for g in GROUPS) else None
        if total is None:
            unchecked.append("nợ nhóm 1–5")
        elif (added := sum(raw[g][0] for g in GROUPS)) != total:
            drop(GROUPS, f"Nợ nhóm 1–5 đọc từ ảnh (trang {fields['group1']['page']}) cộng ra {_printed(added)}, khác dòng tổng {_printed(total)}.")
    for f in ("demand_deposits", "margin_deposits"):
        if f not in from_image:
            continue
        amount, _, at = raw[f]
        parts = []
        for _, ln in note_lines[at + 1:]:
            if not re.search(_SUB_LINE, _fold(ln)) or (part := _amount_after(ln, _SUB_LINE)) is None:
                break
            parts.append(part)
        if len(parts) < 2:
            unchecked.append(LABELS[f].lower())
        elif sum(parts) != amount:
            drop([f], f"{LABELS[f]} đọc từ ảnh là {_printed(amount)} nhưng các dòng con cộng ra {_printed(sum(parts))} (trang {fields[f]['page']}).")
    if "customer_deposits" in fields and ("customer_deposits" in from_image or any(i in ocr for i, _ in note_lines)):
        amount = raw["customer_deposits"][0]
        total = next((_to_decimal(_NUMBER.findall(ln)[0]) for _, ln in note_lines if _TOTAL_LINE.match(_fold(ln))), None)
        if total is None:
            unchecked.append("tiền gửi của khách hàng")
        elif total != amount:  # the note and the balance sheet print the same unit
            drop(["customer_deposits"], f"Tiền gửi của khách hàng đọc từ ảnh là {_printed(amount)} nhưng tổng ở thuyết minh là {_printed(total)}.")
    for x in fields.values():
        if x["page"] - 1 in ocr:
            x["ocr"] = True
    head = (f"Đã nhận dạng chữ từ ảnh (OCR) {len(ocr)} trang: số đọc từ ảnh có thể sai chữ số; ô nào không khớp dòng tổng đã để trống, "
            "các ô còn lại vẫn cần so với file trước khi lưu.")
    tail = [f"Chưa đối chiếu được với dòng tổng: {', '.join(unchecked)}."] if unchecked else []
    return [head, *notes, *tail]


class UnsafeUrl(ValueError):
    pass


def check_public_https(url: str, *, resolve: Callable[[str], list[str]] | None = None) -> None:
    """Refuse anything but https to a public address: the owner pastes the link, the server fetches it."""
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise UnsafeUrl("Chỉ nhận đường dẫn https.")
    resolve = resolve or (lambda host: [info[4][0] for info in socket.getaddrinfo(host, 443)])
    try:
        addresses = resolve(parts.hostname)
    except OSError as exc:
        raise UnsafeUrl("Không phân giải được tên miền.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise UnsafeUrl("Đường dẫn trỏ tới địa chỉ nội bộ.")
