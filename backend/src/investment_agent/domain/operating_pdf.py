"""Proposed values for an operating group (Số liệu vận hành) from the text of a public PDF bulletin. Nothing is saved: the owner sees
each candidate with its page and the line it came from, checks the unit, and confirms. No AI: plain text matching.

For each of the group's lines, the PDF's text lines that contain its name (case and accents aside) are taken in order; the first
number after the name on each is a candidate, up to three. Numbers read the Vietnamese way (dots group thousands, a comma marks the
decimals); a year (1900–2100 standing alone) and parts of a date (10/2026) are skipped.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation

MAX_CANDIDATES = 3
IMAGE_ONLY = "PDF không có chữ (bản scan ảnh): hãy nhập tay."
_NUMBER = re.compile(r"(?<![\d/.,])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?)(?![\d/]|[.,]\d)")


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return re.sub(r"\s+", " ", "".join(c for c in folded if unicodedata.category(c) != "Mn")).lower()


def parse_number(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def _first_number(after: str) -> Decimal | None:
    for m in _NUMBER.finditer(after):
        raw = m.group(1)
        if re.fullmatch(r"(19|20)\d{2}", raw):  # a year standing alone
            continue
        value = parse_number(raw)
        if value is not None:
            return value
    return None


def propose_values(pages: list[str], series: list[str]) -> dict:
    if not any(p.strip() for p in pages):
        return {"values": {}, "missing": list(series), "warnings": [IMAGE_ONLY]}
    values: dict[str, list[dict]] = {}
    for name in series:
        key = _plain(name.strip())
        found = []
        for number, page in enumerate(pages, start=1):
            for line in page.splitlines():
                plain = _plain(line)
                at = plain.find(key) if key else -1
                if at < 0:
                    continue
                value = _first_number(plain[at + len(key):])
                if value is not None:
                    found.append({"value": format(value.normalize(), "f") if value != 0 else "0", "page": number, "text": line.strip()[:200]})
                if len(found) >= MAX_CANDIDATES:
                    break
            if len(found) >= MAX_CANDIDATES:
                break
        if found:
            values[name] = found
    return {"values": values, "missing": [s for s in series if s not in values], "warnings": []}
