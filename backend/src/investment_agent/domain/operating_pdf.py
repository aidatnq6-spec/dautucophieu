"""Proposed values for an operating group (Số liệu vận hành) from the text of a public PDF bulletin. Nothing is saved: the owner sees
each candidate with its page and the line it came from, checks the unit, and confirms. No AI: plain text matching.

For each of the group's lines, the PDF's text lines that contain its name (case and accents aside) are taken in order; the first
number after the name on each is a candidate, up to three. Numbers read the Vietnamese way (dots group thousands, a comma marks the
decimals); a year (1900–2100 standing alone), parts of a date (10/2026) and digits glued to letters (Q3, an OCR "th6p") are skipped.
When the first number is not written the Vietnamese way (3.5, 1,234,567, 12.5%) that line gives no candidate: the number after it
is something else (often the growth rate). Pages whose text is broken (font glyph names such as /Ohorn.dotbl, or many words with
digits inside, as a poor OCR layer on a scan gives) give no candidates and are named in a warning.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation

MAX_CANDIDATES = 3
IMAGE_ONLY = "PDF không có chữ (bản scan ảnh): hãy nhập tay."
_TOKEN = re.compile(r"\d[\d.,]*")
_VIETNAMESE = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")
_GLYPH = re.compile(r"/(?:[A-Za-z]+\.)?[A-Za-z]*(?:horn|acute|grave|hook|tilde|dotbl|cir|breve|dcroat)|/[A-Z]\d{3}")
_DIGIT_INSIDE = re.compile(r"[^\W\d_]\d+[^\W\d_]")
_WORD = re.compile(r"\w+")


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return re.sub(r"\s+", " ", "".join(c for c in folded if unicodedata.category(c) != "Mn")).lower()


def parse_number(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def _first_number(after: str) -> Decimal | None:
    for m in _TOKEN.finditer(after):
        raw = m.group(0).rstrip(".,")
        before = after[m.start() - 1] if m.start() else " "
        follow = after[m.start() + len(raw)] if m.start() + len(raw) < len(after) else " "
        if before.isalpha() or follow.isalpha():  # Q3, th6p, 48ok: part of a word
            continue
        if before == "/" or follow == "/" or re.fullmatch(r"(19|20)\d{2}", raw):  # a date part or a year standing alone
            continue
        return parse_number(raw) if _VIETNAMESE.fullmatch(raw) else None
    return None


def _broken(page: str) -> bool:
    if len(_GLYPH.findall(page)) >= 3:
        return True
    words = _WORD.findall(page)
    inside = sum(1 for w in words if _DIGIT_INSIDE.search(w))
    return inside >= 3 and inside >= 0.02 * len(words)


def propose_values(pages: list[str], series: list[str]) -> dict:
    if not any(p.strip() for p in pages):
        return {"values": {}, "missing": list(series), "warnings": [IMAGE_ONLY]}
    broken = [n for n, page in enumerate(pages, start=1) if page.strip() and _broken(page)]
    values: dict[str, list[dict]] = {}
    for name in series:
        key = _plain(name.strip())
        found = []
        for number, page in enumerate(pages, start=1):
            if number in broken:
                continue
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
    warnings = [f"Chữ ở trang {', '.join(map(str, broken))} bị lỗi phông hoặc nhận dạng kém: không lấy số từ các trang này, hãy nhập tay."] if broken else []
    return {"values": values, "missing": [s for s in series if s not in values], "warnings": warnings}
