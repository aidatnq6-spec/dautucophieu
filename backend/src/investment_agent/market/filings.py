"""Văn bản công bố (owner, 28/11/2026; docs/superpowers/specs/2026-11-28-van-ban-cong-bo-design.md).

The 20:00 run reads watched tickers' own filings (financial statements from the company's shareholder page, board resolutions from
that page and VNDirect's news) on this machine and keeps their text page by page in data/filings/<MÃ>/<id>.json; the public MCP tool
van_ban_cong_bo searches that text. Nothing here is summarised or interpreted: the pages are kept as read, OCR mistakes included.
"""

import hashlib
import html
import json
import re
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
_ID = re.compile(r"^[0-9a-f]{16}$")


def _fold(ch: str) -> str:
    """One character without accents, lower case, đ as d: one character in, one out, so positions stay put."""
    if ch in "đĐ":
        return "d"
    base = unicodedata.normalize("NFD", ch)[0].lower()
    return base[0] if base else ch


def plain(text: str) -> str:
    return "".join(_fold(c) for c in text)


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.found.append((self._href, "".join(self._text)))
            self._href = None


def links_on_page(page_html: str, page_url: str) -> list[dict]:
    """Every link to a PDF on a page, as an absolute url with its label (tags dropped, spaces collapsed)."""
    parser = _Links()
    parser.feed(page_html)
    out, seen = [], set()
    for href, text in parser.found:
        url = urljoin(page_url, html.unescape(href.strip()))
        if not url.lower().split("?")[0].endswith(".pdf") or url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "nhan": re.sub(r"\s+", " ", text).strip()})
    return out


_STATEMENTS = ("bctc", "bao cao tai chinh")
_PARENT_ONLY = ("cong ty me", "rieng")
_RESOLUTIONS = ("nghi quyet", "nq hdqt", "quyet dinh", "dhdcd")


def classify(label: str) -> str | None:
    """bctc for a consolidated (or only) financial statement, nghi_quyet for a resolution or decision, None for anything else."""
    p = plain(label)
    if any(k in p for k in _STATEMENTS):
        return None if any(k in p for k in _PARENT_ONLY) else "bctc"
    return "nghi_quyet" if any(k in p for k in _RESOLUTIONS) else None


def _day(y: int, m: int, d: int) -> str | None:
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return None


def label_date(label: str, url: str) -> str | None:
    """The day in the label's "(dd/mm/yyyy)", else the /YYYYMMDD- the url starts its file name with; None when neither is a real day."""
    found = re.search(r"\((\d{1,2})/(\d{1,2})/(\d{4})\)", label)
    if found:
        return _day(int(found.group(3)), int(found.group(2)), int(found.group(1)))
    found = re.search(r"/(\d{4})(\d{2})(\d{2})[-_]", url)
    return _day(int(found.group(1)), int(found.group(2)), int(found.group(3))) if found else None


def doc_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


class FilingStore:
    """data/filings/<MÃ>/<id>.json, one file a document, and _state.json for files skipped or failing."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def _folder(self, ma: str) -> Path:
        if not _SYMBOL.fullmatch(ma or ""):
            raise ValueError("invalid symbol")
        return self.root / ma

    def read(self, ma: str, doc: str) -> dict | None:
        if not _ID.fullmatch(doc or ""):
            return None
        path = self._folder(ma) / f"{doc}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def save(self, record: dict) -> None:
        folder = self._folder(record["ma"])
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / f"{record['id']}.json.tmp"
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        tmp.replace(folder / f"{record['id']}.json")

    def records(self, ma: str) -> list[dict]:
        """Every stored document of the ticker with its pages, newest first (undated last); a file that does not read is left out."""
        folder = self._folder(ma)
        out = []
        for path in folder.glob("*.json") if folder.is_dir() else []:
            try:
                out.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return sorted(out, key=lambda r: (r.get("ngay") is not None, r.get("ngay") or "", r.get("lay_luc") or ""), reverse=True)

    def list(self, ma: str) -> list[dict]:
        return [{k: v for k, v in r.items() if k != "trang"} for r in self.records(ma)]

    def state(self) -> dict:
        path = self.root / "_state.json"
        try:
            return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        except (OSError, ValueError):
            return {}

    def save_state(self, state: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "_state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def snippets(records: list[dict], keyword: str, *, width: int = 600, limit: int = 12) -> tuple[list[dict], bool]:
    """Passages around each match of the keyword (accents and case ignored), in the records' order, at most `limit`; True when more
    matched than were returned."""
    needle = plain(keyword).strip()
    if not needle:
        return [], False
    found = []
    for rec in records:
        for number, page in enumerate(rec.get("trang") or [], start=1):
            folded, at = plain(page), 0
            while (pos := folded.find(needle, at)) >= 0:
                if len(found) == limit:
                    return found, True
                start = max(0, pos - (width - len(needle)) // 2)
                text = re.sub(r"\s+", " ", page[start:start + width]).strip()
                found.append({"tieu_de": rec.get("tieu_de"), "ngay": rec.get("ngay"), "loai": rec.get("loai"), "trang": number,
                              "nguon": rec.get("nguon"), "doan": text})
                at = start + width
    return found, False
