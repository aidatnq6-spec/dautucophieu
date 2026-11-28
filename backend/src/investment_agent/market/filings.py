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


SOURCES_FILE = "report-sources.json"
NEWS_URL = "https://api-finfo.vndirect.com.vn/v4/news?q=tagCodes:{ma}~newsDate:gte:{since}&size=100&sort=newsDate:desc"
NEWS_KINDS = {"resolutions", "meeting", "other_rights", "management_reports"}
MAX_BYTES, MAX_PAGES, MAX_ATTEMPTS = 30 * 1024 * 1024, 120, 3
SINCE = "2026-04-01"


def _file_key(url: str) -> str:
    """The file name folded to letters and digits, "sign" and a trailing copy number dropped: the same file under the company's
    name and VNDirect's (20260818-kdh-cbtt-nq-...-cong-ty-con-1.pdf, "20260818 - KDH - CBTT NQ ... Cong ty con sign.pdf")."""
    from urllib.parse import unquote
    name = plain(unquote(url.rsplit("/", 1)[-1].split("?")[0]))
    name = re.sub(r"\.pdf$", "", name)
    name = re.sub(r"[^a-z0-9]+", " ", name).split()
    name = [w for w in name if w != "sign"]
    if len(name) > 1 and re.fullmatch(r"\d{1,2}", name[-1]):
        name = name[:-1]
    return "".join(name)


def _label_key(label: str) -> str:
    text = re.sub(r"\([^)]*\)", " ", plain(label))
    text = re.sub(r"^[a-z0-9]{3,10}\s*:\s*", "", text.strip())
    return re.sub(r"[^a-z0-9]+", "", text)


def _sources(data_dir: Path) -> dict:
    path = Path(data_dir) / SOURCES_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        return {}


def _candidates(ma: str, source: dict, *, get_text, sleep, since: str, page_errors: dict) -> list[dict]:
    """The PDFs to keep for one ticker: the company's pages first (they carry decisions VNDirect lacks), then VNDirect's news."""
    found = []
    for field in ("bctc", "cbtt"):
        url = source.get(field)
        if not url:
            continue
        try:
            page = get_text(url)
        except Exception as exc:  # noqa: BLE001 - one page failing leaves the other sources
            page_errors[f"{ma} {field}"] = f"error:{type(exc).__name__}"
            continue
        finally:
            sleep(1)
        for link in links_on_page(page, url):
            kind = classify(link["nhan"])
            if kind:
                found.append({"url": link["url"], "nhan": link["nhan"], "loai": kind,
                              "ngay": label_date(link["nhan"], link["url"]), "trang_nguon": url})
    try:
        rows = json.loads(get_text(NEWS_URL.format(ma=ma, since=since))).get("data") or []
    except Exception as exc:  # noqa: BLE001
        page_errors[f"{ma} vndirect"] = f"error:{type(exc).__name__}"
        rows = []
    finally:
        sleep(1)
    for row in rows:
        if row.get("newsType") not in NEWS_KINDS:
            continue
        for att in row.get("attachments") or []:
            url = str(att.get("url") or "")
            if url.lower().split("?")[0].endswith(".pdf"):
                title = str(row.get("newsTitle") or "").strip()
                found.append({"url": url, "nhan": title, "loai": "nghi_quyet", "ngay": str(row.get("newsDate") or "")[:10] or None,
                              "trang_nguon": row.get("dstockUrl")})
    kept, files, labels = [], set(), set()
    for c in found:
        if c["ngay"] is not None and c["ngay"] < since:
            continue
        fkey, lkey = _file_key(c["url"]), (c["ngay"], _label_key(c["nhan"]))
        if fkey in files or (c["ngay"] and lkey in labels):
            continue
        files.add(fkey)
        labels.add(lkey)
        kept.append({**c, "ma": ma, "id": doc_id(c["url"])})
    return kept


def sync_filings(data_dir: Path, symbols: list[str], *, get_text, get_bytes, read_pdf, now, clock=None, sleep=None,
                 max_files: int = 4, budget_seconds: float = 1500, since: str = SINCE) -> dict:
    """Read up to max_files new filings of the given tickers within the time budget: statements before resolutions, newest first.
    read_pdf(bytes) -> (page texts, pages read by OCR). A file over 30 MB or 120 pages is skipped for good; one that fails is tried
    again on the next three nights; what the budget leaves stays pending."""
    import time
    clock, sleep = clock or time.monotonic, sleep or time.sleep
    store = FilingStore(Path(data_dir) / "filings")
    state, sources, page_errors = store.state(), _sources(data_dir), {}
    todo = []
    for ma in symbols:
        if not _SYMBOL.fullmatch(ma or ""):
            continue
        for c in _candidates(ma, sources.get(ma) or {}, get_text=get_text, sleep=sleep, since=since, page_errors=page_errors):
            seen = state.get(c["id"]) or {}
            if seen.get("skipped") or seen.get("attempts", 0) >= MAX_ATTEMPTS or store.read(ma, c["id"]) is not None:
                continue
            todo.append(c)
    todo.sort(key=lambda c: (c["loai"] == "bctc", c["ngay"] is not None, c["ngay"] or ""), reverse=True)
    read, skipped, errors, start, tried = [], {}, {}, clock(), 0
    for c in todo:
        if tried >= max_files or clock() - start >= budget_seconds:
            break
        tried += 1
        entry = state.setdefault(c["id"], {"ma": c["ma"], "nguon": c["url"]})
        try:
            data = get_bytes(c["url"])
            if len(data) > MAX_BYTES:
                entry["skipped"] = skipped[c["id"]] = "tệp quá 30 MB"
                continue
            pages, ocr_pages = read_pdf(data)
            if len(pages) > MAX_PAGES:
                entry["skipped"] = skipped[c["id"]] = "quá 120 trang"
                continue
        except Exception as exc:  # noqa: BLE001 - one file failing never stops the others
            entry["attempts"] = entry.get("attempts", 0) + 1
            errors[c["id"]] = f"error:{type(exc).__name__}"
            continue
        finally:
            store.save_state(state)
        store.save({"ma": c["ma"], "id": c["id"], "loai": c["loai"], "tieu_de": c["nhan"], "ngay": c["ngay"], "nguon": c["url"],
                    "trang_nguon": c["trang_nguon"], "lay_luc": now.isoformat(), "so_trang": len(pages), "ocr": ocr_pages,
                    "trang": pages})
        state.pop(c["id"], None)
        store.save_state(state)
        read.append(c["id"])
    out = {"read": read, "skipped": skipped, "errors": errors, "pending": len(todo) - tried}
    return {**out, **({"page_errors": page_errors} if page_errors else {})}


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
