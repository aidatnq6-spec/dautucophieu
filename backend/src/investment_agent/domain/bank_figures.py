"""Số liệu ngân hàng nhập tay: loans by group 1–5, customer deposits and CAR per quarter, and the ratios the owner's
spreadsheet computes from them. No free source publishes these (checked 31/10/2026), so the owner enters them from the
notes to the quarterly statements, or has them read from a public PDF and confirms before saving.

The PDF reader only proposes values: each comes with its page, amounts are converted to tỷ đồng only when the page (or
an earlier one) states its unit, and a label not found is reported missing, never filled in.
"""

import ipaddress
import re
import socket
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Callable
from urllib.parse import urlsplit

GROUPS = ("group1", "group2", "group3", "group4", "group5")
FIELDS = (*GROUPS, "demand_deposits", "margin_deposits", "customer_deposits", "car")
LABELS = {"group1": "Nợ nhóm 1 (đủ tiêu chuẩn)", "group2": "Nợ nhóm 2 (cần chú ý)", "group3": "Nợ nhóm 3 (dưới tiêu chuẩn)",
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
            "car": str((car / 100).quantize(_Q4, ROUND_HALF_UP)) if car is not None else None}


# ---- reading a public PDF of the quarterly statements -------------------------------------------------------------

_NUMBER = re.compile(r"\(?-?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?\)?|\(?-?\d+(?:[.,]\d+)?\)?%?")
_UNITS = ((re.compile(r"đơn vị[^\n]{0,20}?triệu", re.I), Decimal(1000)), (re.compile(r"đơn vị[^\n]{0,20}?tỷ", re.I), Decimal(1)),
          (re.compile(r"đơn vị[^\n]{0,20}?(?:đồng|vnd)", re.I), Decimal(1_000_000_000)))
_LINE_LABELS = {"group1": r"nợ đủ tiêu chuẩn", "group2": r"nợ cần chú ý", "group3": r"nợ dưới tiêu chuẩn", "group4": r"nợ nghi ngờ",
                "group5": r"nợ có khả năng mất vốn", "demand_deposits": r"tiền gửi không kỳ hạn", "margin_deposits": r"tiền gửi ký quỹ",
                "customer_deposits": r"(?:^|\s)tiền gửi của khách hàng"}
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
    m = re.search(label, line, re.I)
    if not m:
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


def parse_report_pages(pages: list[str]) -> dict:
    """Proposed values {field: {value (tỷ đồng, CAR in %), page (1-based)}}, the fields not found, and warnings."""
    if not any(p.strip() for p in pages):
        return {"fields": {}, "missing": list(FIELDS), "warnings": [IMAGE_ONLY]}
    fields, warnings, unit = {}, [], None
    units = []
    for text in pages:
        unit = next((u for pattern, u in _UNITS if pattern.search(text)), unit)  # a page without a unit line inherits the last one
        units.append(unit)
    lines = [[ln for ln in p.splitlines()] for p in pages]
    customer_note = [i for i, p in enumerate(pages) if re.search(r"ký quỹ", p, re.I) and re.search(r"vốn chuyên dùng", p, re.I)]
    unitless = False

    def take(field: str, page_indexes) -> None:
        nonlocal unitless
        for i in page_indexes:
            for ln in lines[i]:
                amount = _amount_after(ln, _LINE_LABELS[field])
                if amount is None:
                    continue
                if units[i] is None:
                    unitless = True
                    return
                fields[field] = {"value": _plain(amount / units[i]), "page": i + 1}
                return

    everywhere = range(len(pages))
    # Loan groups: the page carrying most of the five labels with amounts (the loan-quality note).
    group_page = max(everywhere, key=lambda i: sum(1 for g in GROUPS if any(_amount_after(ln, _LINE_LABELS[g]) is not None for ln in lines[i])))
    for g in GROUPS:
        take(g, [group_page])
    for f in ("demand_deposits", "margin_deposits"):  # only from the customer-deposit note: deposits at other banks share the labels
        take(f, customer_note)
    take("customer_deposits", everywhere)
    for i, text in enumerate(pages):
        m = re.search(r"an toàn vốn[^\n%]*?(\d{1,2}(?:[.,]\d+)?)\s*%", text, re.I)
        if m:
            fields["car"] = {"value": _plain(_to_decimal(m.group(1))), "page": i + 1}
            break
    if unitless:
        warnings.append("Không thấy dòng đơn vị (triệu/tỷ đồng) trên trang có số; không điền để tránh sai đơn vị.")
    if not customer_note:
        warnings.append("Không thấy thuyết minh tiền gửi của khách hàng (có dòng ký quỹ và vốn chuyên dùng).")
    return {"fields": fields, "missing": [f for f in FIELDS if f not in fields], "warnings": warnings}


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
