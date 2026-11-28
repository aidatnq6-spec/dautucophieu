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
    try:
        parser.feed(page_html)
    except Exception:  # noqa: BLE001 - html.parser gives up on garbage (a site serving binary as text): keep what came before it
        pass
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
_RESOLUTION_FIRST = ("nghi quyet", "nq ", "quyet dinh", "bien ban", "cbtt nq")


def is_parent_only(label: str) -> bool:
    """The parent company's own statement ("Công ty Mẹ", "riêng"), not a consolidated one ("hợp nhất Công ty mẹ và các công ty con")."""
    p = plain(label)
    return "hop nhat" not in p and any(k in p for k in _PARENT_ONLY)


def classify(label: str) -> str | None:
    """bctc for a financial statement, nghi_quyet for a resolution or decision (also one that approves a statement), None otherwise.
    A parent-only statement is still bctc: the sync drops it only when a consolidated one carries the same day."""
    p = plain(label).strip()
    if p.startswith(_RESOLUTION_FIRST):
        return "nghi_quyet"
    if any(k in p for k in _STATEMENTS):
        return "bctc"
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


USER_AGENT = "investment-agent/0.1 (personal use)"
ROBOTS_NO = "robots.txt không cho đọc"


def _file_key(url: str) -> str:
    """The file name folded to letters and digits with "sign" dropped, to match a company's file with VNDirect's copy of it
    (20260818-kdh-cbtt-nq-...-cong-ty-con-1.pdf, "20260818 - KDH - CBTT NQ ... Cong ty con sign.pdf")."""
    from urllib.parse import unquote
    name = plain(unquote(url.rsplit("/", 1)[-1].split("?")[0]))
    name = re.sub(r"\.pdf$", "", name)
    return "".join(w for w in re.sub(r"[^a-z0-9]+", " ", name).split() if w != "sign")


def _same_file(company_key: str, vndirect_key: str) -> bool:
    """VNDirect's copy of a company's file: the same name, or the company's with a copy number after it ("...-1")."""
    rest = company_key[len(vndirect_key):] if company_key.startswith(vndirect_key) else None
    return bool(vndirect_key) and rest is not None and re.fullmatch(r"\d{0,2}", rest) is not None


def _robots(url: str, get_text, cache: dict) -> bool:
    """Whether robots.txt of the url's site lets this app read it. No robots.txt (404, 410) allows all; any other failure to read it
    allows nothing tonight."""
    from urllib.parse import urlsplit
    from urllib.robotparser import RobotFileParser
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in cache:
        parser = RobotFileParser()
        try:
            parser.parse(get_text(origin + "/robots.txt").splitlines())
        except Exception as exc:  # noqa: BLE001
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status not in (404, 410):
                cache[origin] = None
                return False
            parser.parse([])
        cache[origin] = parser
    parser = cache[origin]
    return parser is not None and parser.can_fetch(USER_AGENT, url)


def _sources(data_dir: Path) -> dict:
    path = Path(data_dir) / SOURCES_FILE
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        return {}


def _candidates(ma: str, source: dict, *, get_text, sleep, since: str, page_errors: dict, robots: dict) -> list[dict]:
    """The PDFs to keep for one ticker: the company's pages first (they carry decisions VNDirect lacks), then VNDirect's news.
    Distinct urls stay distinct; a VNDirect attachment is dropped only when it is the company's own file; a parent-only statement is
    dropped when a consolidated one carries the same day."""
    company, vndirect = [], []
    for field in ("bctc", "cbtt"):
        url = source.get(field)
        if not url:
            continue
        if not _robots(url, get_text, robots):
            page_errors[f"{ma} {field}"] = ROBOTS_NO
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
                company.append({"url": link["url"], "nhan": link["nhan"], "loai": kind, "ngay": label_date(link["nhan"], link["url"]),
                                "trang_nguon": url, "robots": _robots(link["url"], get_text, robots)})
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
                vndirect.append({"url": url, "nhan": str(row.get("newsTitle") or "").strip(), "loai": "nghi_quyet",
                                 "ngay": str(row.get("newsDate") or "")[:10] or None, "trang_nguon": row.get("dstockUrl"), "robots": True})
    consolidated_days = {c["ngay"] for c in company if c["loai"] == "bctc" and not is_parent_only(c["nhan"])}
    company = [c for c in company if not (c["loai"] == "bctc" and is_parent_only(c["nhan"]) and c["ngay"] in consolidated_days)]
    company_keys = [_file_key(c["url"]) for c in company]
    vndirect = [v for v in vndirect if not any(_same_file(k, _file_key(v["url"])) for k in company_keys)]
    kept, urls = [], set()
    for c in company + vndirect:
        if (c["ngay"] is not None and c["ngay"] < since) or c["url"] in urls:
            continue
        urls.add(c["url"])
        kept.append({**c, "ma": ma, "id": doc_id(c["url"])})
    return kept


def sync_filings(data_dir: Path, symbols: list[str], *, get_text, get_bytes, read_pdf, now, clock=None, sleep=None,
                 max_files: int = 20, budget_seconds: float = 1500, file_seconds: float = 600, since: str = SINCE) -> dict:
    """Read up to max_files new filings of the given tickers within the time budget (counted from the start, source pages included):
    statements before resolutions, newest first; a file starts only when file_seconds of the budget are left. read_pdf(bytes) ->
    (page texts, pages read by OCR[, page numbers OCR could not read]). A file over 30 MB or 120 pages is skipped for good; each start
    counts as an attempt before the download, so a file whose step is killed is not retried for ever; three attempts and it is left.
    What the budget leaves stays pending."""
    import time
    clock, sleep = clock or time.monotonic, sleep or time.sleep
    start = clock()
    store = FilingStore(Path(data_dir) / "filings")
    state, sources, page_errors, robots = store.state(), _sources(data_dir), {}, {}
    todo, skipped = [], {}
    for ma in symbols:
        if not _SYMBOL.fullmatch(ma or ""):
            continue
        for c in _candidates(ma, sources.get(ma) or {}, get_text=get_text, sleep=sleep, since=since, page_errors=page_errors,
                             robots=robots):
            seen = state.get(c["id"]) or {}
            if seen.get("skipped") or seen.get("attempts", 0) >= MAX_ATTEMPTS or store.read(ma, c["id"]) is not None:
                continue
            if not c["robots"]:
                skipped[c["id"]] = ROBOTS_NO
                continue
            todo.append(c)
    todo.sort(key=lambda c: (c["loai"] == "bctc", c["ngay"] is not None, c["ngay"] or ""), reverse=True)
    read, errors, tried = [], {}, 0
    for c in todo:
        if tried >= max_files or budget_seconds - (clock() - start) < file_seconds:
            break
        tried += 1
        entry = state.setdefault(c["id"], {"ma": c["ma"], "nguon": c["url"]})
        entry["attempts"] = entry.get("attempts", 0) + 1
        store.save_state(state)
        try:
            data = get_bytes(c["url"])
            if len(data) > MAX_BYTES:
                entry["skipped"] = skipped[c["id"]] = "tệp quá 30 MB"
                store.save_state(state)
                continue
            result = read_pdf(data)
            pages, ocr_pages = result[0], result[1]
            unread = sorted(result[2]) if len(result) > 2 else []
            if len(pages) > MAX_PAGES:
                entry["skipped"] = skipped[c["id"]] = "quá 120 trang"
                store.save_state(state)
                continue
        except Exception as exc:  # noqa: BLE001 - one file failing never stops the others
            errors[c["id"]] = f"error:{type(exc).__name__}"
            continue
        store.save({"ma": c["ma"], "id": c["id"], "loai": c["loai"], "tieu_de": c["nhan"], "ngay": c["ngay"], "nguon": c["url"],
                    "trang_nguon": c["trang_nguon"], "lay_luc": now.isoformat(), "so_trang": len(pages), "ocr": ocr_pages,
                    "trang_chua_doc": unread, "trang": [unicodedata.normalize("NFC", p) for p in pages]})
        state.pop(c["id"], None)
        store.save_state(state)
        read.append(c["id"])
    out = {"read": read, "skipped": skipped, "errors": errors, "pending": len(todo) - tried}
    return {**out, **({"page_errors": page_errors} if page_errors else {})}


def _folded_with_map(text: str) -> tuple[str, list[int]]:
    """The text folded (plain) with every run of whitespace as one space, and the index in the text of each folded character."""
    out, where = [], []
    for i, ch in enumerate(text):
        if ch.isspace():
            if out and out[-1] == " ":
                continue
            out.append(" ")
        else:
            out.append(_fold(ch))
        where.append(i)
    return "".join(out), where


def snippets(records: list[dict], keyword: str, *, width: int = 600, limit: int = 12) -> tuple[list[dict], bool]:
    """Passages around each match of the keyword (accents, case, line breaks and doubled spaces ignored), in the records' order, at
    most `limit`; True when more matched than were returned. The passage is the page's own text, never the folded one."""
    needle = re.sub(r"\s+", " ", plain(unicodedata.normalize("NFC", keyword))).strip()[: width // 2]
    if not needle:
        return [], False
    found = []
    for rec in records:
        for number, page in enumerate(rec.get("trang") or [], start=1):
            page = unicodedata.normalize("NFC", page)
            folded, where = _folded_with_map(page)
            at, shown_to = 0, -1
            while (pos := folded.find(needle, at)) >= 0:
                at = pos + len(needle)
                origin = where[pos]
                if origin < shown_to:
                    continue
                if len(found) == limit:
                    return found, True
                start = max(0, origin - (width - len(needle)) // 2)
                text = re.sub(r"\s+", " ", page[start:start + width]).strip()
                found.append({"tieu_de": rec.get("tieu_de"), "ngay": rec.get("ngay"), "loai": rec.get("loai"), "trang": number,
                              "nguon": rec.get("nguon"), "doan": text})
                shown_to = start + width
    return found, False
