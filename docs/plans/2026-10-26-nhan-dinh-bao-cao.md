# Nhận định (AI reads public macro and sector reports) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Spec:** `docs/superpowers/specs/2026-10-26-nhan-dinh-bao-cao-design.md` (owner-approved 2026-10-26). The spec is the authority.

**Goal:** When ACBS or the World Bank publishes a new macro, strategy or overview report, extract with AI (public text only) whether the macro picture is favourable now and over 6–12 months, and which ICB sectors benefit or suffer, with verified quotes. Aggregate the reports locally, link the sectors to the watchlist and the Định giá verdicts, show the result on a **Nhận định** page, and send it to Telegram. SSI titles appear as a side signal.

**Architecture:**
- `insights/sources.py` discovers report references: the ACBS list page, then the PDF link on each detail page; the World Bank documents API; SSI title lists.
- `insights/pdf.py` extracts page texts with `pypdf`.
- `insights/extract.py` builds a privacy-safe prompt and calls the existing `OpenRouterGateway` with a JSON schema. It keeps only claims whose quote appears in the text and whose sector is in the closed ICB list.
- `insights/store.py` keeps one JSON per report.
- `insights/summary.py` aggregates locally.
- `insights-run` (CLI and scheduler) ties it together.
- The API route `/internal/insights` adds the local links: watchlist, held tickers, Định giá rows.

**Tech Stack:** Python 3.11, httpx, pypdf (new, pinned), existing `ai/openrouter.py`, `ai/budget.py`, `ai/catalog.py`; FastAPI; Next.js page; pytest; Playwright.

## Global constraints

- **No personal data in any model call.** Messages may contain only the report text, the list of ICB sector names, and instructions. A test asserts that a request built with holdings and watchlist in scope contains none of them.
- **Quotes must be found** in the extracted text after normalisation (casefold, collapse whitespace, drop punctuation). Claims that fail are dropped. A report with no surviving claim stores `status: "no_reliable_claims"` and is not sent.
- **Budget:** the existing `SpendLedger` with `monthly_usd = 2`. When the budget is exhausted, stop the run and record the reason. When `OPENROUTER_API_KEY` is missing, the page says "Chưa cấu hình AI" and reports are not marked processed.
- **Sources:**
  - fetch with User-Agent `investment-agent/0.1 (personal use)`;
  - at most 3 new reports per run, 2 s between downloads;
  - first run only looks at the last 60 days;
  - never log in anywhere, never fetch SSI PDFs.
- **Process:** TDD with each RED watched. Run the full backend suite before each commit and `verify.ps1` before the PR. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Work on a branch from `docs/insights-design` in the worktree.
- **New dependency:** `pypdf==5.1.0`. Install it into both the worktree `.venv` and the main checkout `.venv` with `-m pip install pypdf==5.1.0`, and add it to `backend/pyproject.toml` dependencies.

## Real shapes (checked 2026-10-26)

- **ACBS list page** `https://acbs.com.vn/trung-tam-phan-tich/bao-cao-tong-quan`: detail links `/trung-tam-phan-tich/chi-tiet/<slug>`, about 18 per page, newest first.
  - The detail page holds one PDF link such as `https://acbs.com.vn/acbsmedia/2026/10/202610_MacroUpdate_VN_Final.pdf` (public, about 5 MB, `application/pdf`).
  - The publication date is the `acbsmedia/YYYY/MM/` part of the PDF URL; use the 1st of that month.
- **World Bank** `https://search.worldbank.org/api/v2/wds?format=json&countrycode_exact=VN&rows=50&sort=docdt&order=desc&fl=docdt,display_title,pdfurl,docty`. `documents` is a dict of id → `{docdt, display_title, pdfurl, docty}`, plus a non-dict `facets` key to skip.
  - Keep `docty in {"Report", "Brief"}` and titles matching `(?i)macro monitoring|taking stock|economic update`.
  - The newest such document on 2026-10-26 was 2025-03-11, so expect few or no new World Bank reports.
- **SSI title pages** `https://www.ssi.com.vn/khach-hang-ca-nhan/{bao-cao-vi-mo,bao-cao-nganh,bao-cao-chien-luoc}`: links `/analysis-center/report/download/<slug>`, newest first. Downloads need login, so titles only.
  - Slugs look like `bao-cao-chien-luoc-thang-92026-ra-khoi`. Read the visible title from the anchor text when present, otherwise humanise the slug.

## Interfaces

| Producer | Consumer | Contract |
|---|---|---|
| T1 sources | T4 pipeline | `ReportRef(source, ref_id, title, page_url, pdf_url, published: date)`; `discover_acbs(get, since)`, `discover_worldbank(get, since)`, `ssi_titles(get, limit) -> list[dict(title, url, kind)]` |
| T2 pdf | T3, T4 | `extract_pages(data: bytes, max_pages=60) -> list[str]` |
| T3 extract | T4 | `build_messages(title, pages, sectors) -> list[dict]`, `RESPONSE_FORMAT`, `validate(raw: dict, pages, sectors) -> dict` (cleaned insight) |
| T4 store and pipeline | T5, T6, T7, T8 | `InsightStore(root).seen(source, ref_id)`, `.save(record)`, `.recent(today, days=60)`; `run_insights(...) -> dict` |
| T5 summary | T8 | `summarise(records) -> dict`, `link(summary, sectors, rows, held) -> dict` |

The record JSON, one per report:
```json
{"source": "acbs", "ref_id": "cap-nhat-vi-mo-thang-9-2026", "title": "...", "page_url": "...", "pdf_url": "...", "published": "2026-10-01",
 "processed_at": "...", "status": "ok|no_text|no_reliable_claims", "model": "...", "cost_usd": "0.0031", "telegram_sent": false,
 "insight": {"macro_now": {"view": "favourable|neutral|unfavourable", "reasons": [{"text": "...", "quote": "...", "page": 3}]},
             "macro_outlook": {...same...},
             "sectors": [{"sector": "Ngân hàng", "effect": "benefit|harm", "reason": "...", "quote": "...", "page": 7}]}}
```

---

### Task 1: Report sources

**Files:** Create `backend/src/investment_agent/insights/__init__.py` (empty) and `backend/src/investment_agent/insights/sources.py`. Test: `backend/tests/insights/test_sources.py`.

**Step 1: Failing tests**, using fixtures shaped like the live pages:

```python
import json
from datetime import date

from investment_agent.insights.sources import ReportRef, discover_acbs, discover_worldbank, ssi_titles

ACBS_LIST = """<a href="/trung-tam-phan-tich/chi-tiet/cap-nhat-vi-mo-thang-10-2026">Cập nhật vĩ mô tháng 10/2026</a>
<a href="https://acbs.com.vn/trung-tam-phan-tich/chi-tiet/chien-luoc-q4-2026">Chiến lược Q4/2026</a>
<a href="/trung-tam-phan-tich/chi-tiet/cap-nhat-vi-mo-thang-10-2026">dup</a>"""
ACBS_DETAIL = {
    "cap-nhat-vi-mo-thang-10-2026": '<a href="https://acbs.com.vn/acbsmedia/2026/10/202610_MacroUpdate_VN_Final.pdf">Tải</a>',
    "chien-luoc-q4-2026": '<p>no file</p>',
}


def acbs_get(url):
    if url.endswith("bao-cao-tong-quan"):
        return ACBS_LIST
    return ACBS_DETAIL[url.rsplit("/", 1)[-1]]


def test_acbs_finds_new_reports_with_a_pdf_and_dates_them_from_the_media_path():
    refs = discover_acbs(acbs_get, since=date(2026, 8, 27))
    assert refs == [ReportRef("acbs", "cap-nhat-vi-mo-thang-10-2026", "Cập nhật vĩ mô tháng 10/2026",
                              "https://acbs.com.vn/trung-tam-phan-tich/chi-tiet/cap-nhat-vi-mo-thang-10-2026",
                              "https://acbs.com.vn/acbsmedia/2026/10/202610_MacroUpdate_VN_Final.pdf", date(2026, 10, 1))]
    assert discover_acbs(acbs_get, since=date(2026, 11, 1)) == []  # older than the window


WB = json.dumps({"documents": {
    "D1": {"docdt": "2026-09-30T00:00:00Z", "display_title": "Viet Nam Macro Monitoring", "docty": "Brief", "pdfurl": "http://documents.worldbank.org/x.pdf"},
    "D2": {"docdt": "2026-09-29T00:00:00Z", "display_title": "Procurement Plan", "docty": "Procurement Plan", "pdfurl": "http://d/y.pdf"},
    "D3": {"docdt": "2025-03-11T00:00:00Z", "display_title": "Taking Stock March 2025", "docty": "Report", "pdfurl": "http://d/z.pdf"},
    "facets": {}}})


def test_world_bank_keeps_recent_macro_reports_only():
    refs = discover_worldbank(lambda url: WB, since=date(2026, 8, 27))
    assert [(r.ref_id, r.published) for r in refs] == [("D1", date(2026, 9, 30))]


SSI = """<a href="/analysis-center/report/download/bao-cao-chien-luoc-thang-92026-ra-khoi">Báo cáo chiến lược tháng 9/2026: Ra khơi</a>
<a href="/analysis-center/report/download/cap-nhat-nganh-ngan-hang-tam-diem-lai-suat"><img src="x"></a>"""


def test_ssi_titles_are_listed_without_downloads():
    titles = ssi_titles(lambda url: SSI, limit=5)
    assert titles[0] == {"title": "Báo cáo chiến lược tháng 9/2026: Ra khơi", "kind": "vĩ mô",
                         "url": "https://www.ssi.com.vn/analysis-center/report/download/bao-cao-chien-luoc-thang-92026-ra-khoi"}
    assert titles[1]["title"] == "Cap nhat nganh ngan hang tam diem lai suat"  # no anchor text: humanised slug
```

Note on `kind`: the first page fetched is `bao-cao-vi-mo`, and the fake returns the same HTML for every page, so the titles are deduplicated by URL across pages and keep the first kind seen.

**Step 2:** Run `./.venv/Scripts/python.exe -m pytest backend/tests/insights -q -p no:warnings`. Expected: collection error.

**Step 3: Implement** `sources.py`:

```python
"""Public report discovery: ACBS overview reports (PDF), World Bank documents API (PDF), SSI report titles (no download).

Checked 2026-10-26: ACBS PDFs and the World Bank API are public; SSI PDFs need a login, so only titles are used.
"""

import html
import json
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urljoin

ACBS_LIST = "https://acbs.com.vn/trung-tam-phan-tich/bao-cao-tong-quan"
WB_API = ("https://search.worldbank.org/api/v2/wds?format=json&countrycode_exact=VN&rows=50&sort=docdt&order=desc"
          "&fl=docdt,display_title,pdfurl,docty")
SSI_PAGES = {"vĩ mô": "https://www.ssi.com.vn/khach-hang-ca-nhan/bao-cao-vi-mo", "ngành": "https://www.ssi.com.vn/khach-hang-ca-nhan/bao-cao-nganh",
             "chiến lược": "https://www.ssi.com.vn/khach-hang-ca-nhan/bao-cao-chien-luoc"}
_WB_TITLE = re.compile(r"(?i)macro monitoring|taking stock|economic update")


@dataclass(frozen=True)
class ReportRef:
    source: str
    ref_id: str
    title: str
    page_url: str
    pdf_url: str
    published: date


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def discover_acbs(get, *, since: date) -> list[ReportRef]:
    refs, seen = [], set()
    for m in re.finditer(r'<a[^>]+href="([^"]*/trung-tam-phan-tich/chi-tiet/([a-z0-9-]+))"[^>]*>(.*?)</a>', get(ACBS_LIST), re.S):
        page_url, slug, title = urljoin(ACBS_LIST, m.group(1)), m.group(2), _text(m.group(3))
        if slug in seen:
            continue
        seen.add(slug)
        pdf = re.search(r'href="([^"]*acbsmedia/(\d{4})/(\d{2})/[^"]+\.pdf)"', get(page_url), re.I)
        if not pdf:
            continue
        published = date(int(pdf.group(2)), int(pdf.group(3)), 1)
        if published >= since.replace(day=1):
            refs.append(ReportRef("acbs", slug, title, page_url, urljoin(page_url, pdf.group(1)), published))
    return refs


def discover_worldbank(get, *, since: date) -> list[ReportRef]:
    refs = []
    for doc_id, d in json.loads(get(WB_API)).get("documents", {}).items():
        if not isinstance(d, dict) or "docdt" not in d:
            continue
        title = re.sub(r"\s+", " ", d.get("display_title", "")).strip()
        published = date.fromisoformat(d["docdt"][:10])
        if d.get("docty") in {"Report", "Brief"} and _WB_TITLE.search(title) and d.get("pdfurl") and published >= since:
            refs.append(ReportRef("worldbank", doc_id, title, d["pdfurl"], d["pdfurl"], published))
    return sorted(refs, key=lambda r: r.published, reverse=True)


def ssi_titles(get, *, limit: int = 10) -> list[dict]:
    out, seen = [], set()
    for kind, url in SSI_PAGES.items():
        for m in re.finditer(r'<a[^>]+href="(/analysis-center/report/download/([a-z0-9-]+))"[^>]*>(.*?)</a>', get(url), re.S):
            full = urljoin(url, m.group(1))
            if full in seen:
                continue
            seen.add(full)
            title = _text(m.group(3)) or m.group(2).replace("-", " ").capitalize()
            out.append({"title": title, "kind": kind, "url": full})
    return out[:limit]
```

**Step 4:** Run the tests; expect 3 passed. Then run the suite.

**Step 5:** Commit `feat: public report discovery (ACBS, World Bank, SSI titles)`.

---

### Task 2: PDF text extraction

**Files:** Create `backend/src/investment_agent/insights/pdf.py`. Test: `backend/tests/insights/test_pdf.py`. Modify `backend/pyproject.toml` (add `"pypdf==5.1.0"` to `dependencies`).

**Step 0:** Install `pypdf==5.1.0` into the worktree `.venv` and the main checkout `.venv`.

**Step 1: Failing test.** Build a 2-page PDF in the test with a minimal hand-written PDF, so no extra library is needed:

```python
from investment_agent.insights.pdf import extract_pages


def tiny_pdf(texts):
    objs, kids = [], []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(None)  # pages, filled below
    font_id = 3
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for t in texts:
        stream = f"BT /F1 12 Tf 72 720 Td ({t}) Tj ET".encode()
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        content_id = len(objs)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode())
        kids.append(len(objs))
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode()
    out, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


def test_pages_are_extracted_in_order_and_capped():
    pages = extract_pages(tiny_pdf(["GDP growth 7.5 percent", "Banks benefit from rates", "third"]), max_pages=2)
    assert len(pages) == 2 and "GDP growth 7.5 percent" in pages[0] and "Banks benefit" in pages[1]


def test_unreadable_bytes_give_no_pages():
    assert extract_pages(b"not a pdf") == []
```

**Step 2:** Run it. Expect an ImportError (module missing).

**Step 3: Implement**

```python
"""Text per page from a PDF (pypdf). Image-only or unreadable files give no pages; no OCR."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_pages(data: bytes, *, max_pages: int = 60) -> list[str]:
    try:
        reader = PdfReader(BytesIO(data))
        return [(page.extract_text() or "") for page in reader.pages[:max_pages]]
    except (PdfReadError, ValueError, KeyError, TypeError):
        return []
```

**Step 4:** Run the tests; expect them to pass, then the suite. **Step 5:** Commit `feat: PDF text extraction for reports` (include `pyproject.toml`).

---

### Task 3: Privacy-safe AI extraction and quote validation

**Files:** Create `backend/src/investment_agent/insights/extract.py` and `backend/src/investment_agent/ai/prompts/insights-vi-1.txt`. Test: `backend/tests/insights/test_extract.py`.

**Step 1: Failing tests**

```python
import json

from investment_agent.insights.extract import RESPONSE_FORMAT, build_messages, normalise, validate

SECTORS = ["Ngân hàng", "Bất động sản", "Dầu khí"]
PAGES = ["Tăng trưởng GDP quý III đạt 7,5%, cao hơn kỳ vọng.", "Lãi suất thấp hỗ trợ ngành ngân hàng; giá dầu giảm gây áp lực lên doanh nghiệp dầu khí."]


def test_messages_carry_only_report_text_sectors_and_instructions():
    msgs = build_messages("Cập nhật vĩ mô tháng 10/2026", PAGES, SECTORS)
    blob = json.dumps(msgs, ensure_ascii=False)
    assert "[Trang 1]" in blob and "[Trang 2]" in blob and "Ngân hàng" in blob
    for private in ("MBB", "SSI", "HPG", "KDH", "watchlist", "danh mục của", "đang nắm", "giá vốn"):
        assert private not in blob
    assert RESPONSE_FORMAT["type"] == "json_schema"


def test_validate_keeps_quoted_claims_and_drops_invented_or_unknown_ones():
    raw = {"macro_now": {"view": "favourable", "reasons": [
               {"text": "GDP tăng mạnh", "quote": "Tăng trưởng GDP quý III đạt 7,5%", "page": 1},
               {"text": "bịa", "quote": "Lạm phát vượt 10%", "page": 1}]},
           "macro_outlook": {"view": "neutral", "reasons": []},
           "sectors": [{"sector": "Ngân hàng", "effect": "benefit", "reason": "lãi suất thấp", "quote": "lãi suất thấp hỗ trợ ngành ngân hàng", "page": 2},
                       {"sector": "Hàng không", "effect": "harm", "reason": "x", "quote": "giá dầu giảm", "page": 2},
                       {"sector": "Dầu khí", "effect": "harm", "reason": "giá dầu giảm", "quote": "giá dầu giảm gây áp lực", "page": 1}]}
    out = validate(raw, PAGES, SECTORS)
    assert [r["text"] for r in out["macro_now"]["reasons"]] == ["GDP tăng mạnh"]
    assert [(s["sector"], s["effect"]) for s in out["sectors"]] == [("Ngân hàng", "benefit")]  # unknown sector and wrong page dropped
    assert out["dropped"] == 3


def test_normalise_ignores_case_spacing_and_punctuation():
    assert normalise("  Lãi suất   THẤP, hỗ-trợ ") == normalise("lãi suất thấp hỗ trợ")
```

**Step 2:** Run it. Expect an ImportError.

**Step 3: Implement.** `insights-vi-1.txt` holds the Vietnamese system instructions:
- read only the given report;
- answer in Vietnamese;
- `view` is one of favourable / neutral / unfavourable for the current macro picture and for the 6–12 month outlook, with 3–5 reasons;
- sectors come only from the given list, with effect benefit / harm;
- every reason and sector carries an exact quote copied verbatim from the page and its page number;
- if the report does not say, return fewer items; never invent;
- no investment advice.

`extract.py`:

```python
"""Per-report extraction: prompt built from public report text only, JSON schema output, quotes verified locally."""

import re
import unicodedata
from importlib import resources

VIEW = {"type": "string", "enum": ["favourable", "neutral", "unfavourable"]}
REASON = {"type": "object", "additionalProperties": False, "required": ["text", "quote", "page"],
          "properties": {"text": {"type": "string"}, "quote": {"type": "string"}, "page": {"type": "integer"}}}
MACRO = {"type": "object", "additionalProperties": False, "required": ["view", "reasons"],
         "properties": {"view": VIEW, "reasons": {"type": "array", "items": REASON, "maxItems": 5}}}
RESPONSE_FORMAT = {"type": "json_schema", "json_schema": {"name": "report_insight", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["macro_now", "macro_outlook", "sectors"],
    "properties": {"macro_now": MACRO, "macro_outlook": MACRO, "sectors": {"type": "array", "maxItems": 12, "items": {
        "type": "object", "additionalProperties": False, "required": ["sector", "effect", "reason", "quote", "page"],
        "properties": {"sector": {"type": "string"}, "effect": {"type": "string", "enum": ["benefit", "harm"]}, "reason": {"type": "string"},
                       "quote": {"type": "string"}, "page": {"type": "integer"}}}}}}}}
MAX_CHARS = 120_000  # keeps one request well under the per-request budget


def _instructions() -> str:
    return resources.files("investment_agent.ai.prompts").joinpath("insights-vi-1.txt").read_text(encoding="utf-8")


def build_messages(title: str, pages: list[str], sectors: list[str]) -> list[dict]:
    body, used = [], 0
    for i, text in enumerate(pages, start=1):
        chunk = f"[Trang {i}]\n{text.strip()}\n"
        if used + len(chunk) > MAX_CHARS:
            break
        body.append(chunk)
        used += len(chunk)
    user = f"Tiêu đề báo cáo: {title}\nDanh sách ngành được phép: {', '.join(sectors)}\n\n" + "\n".join(body)
    return [{"role": "system", "content": _instructions()}, {"role": "user", "content": user}]


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text).casefold()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()


def _found(quote: str, page: int, pages: list[str]) -> bool:
    q = normalise(quote)
    return bool(q) and 1 <= page <= len(pages) and q in normalise(pages[page - 1])


def validate(raw: dict, pages: list[str], sectors: list[str]) -> dict:
    dropped, allowed = 0, set(sectors)
    out = {}
    for key in ("macro_now", "macro_outlook"):
        block = raw.get(key) or {}
        reasons = [r for r in block.get("reasons", []) if _found(r.get("quote", ""), int(r.get("page", 0)), pages)]
        dropped += len(block.get("reasons", [])) - len(reasons)
        out[key] = {"view": block.get("view") if block.get("view") in VIEW["enum"] else "neutral", "reasons": reasons}
    kept = [s for s in raw.get("sectors", []) if s.get("sector") in allowed and s.get("effect") in ("benefit", "harm")
            and _found(s.get("quote", ""), int(s.get("page", 0)), pages)]
    dropped += len(raw.get("sectors", [])) - len(kept)
    out["sectors"], out["dropped"] = kept, dropped
    return out
```

In the validate test the "Dầu khí" claim cites page 1, but its quote is on page 2, so it is dropped (3 dropped in total). Make sure the prompt asks for the page the quote is on. Include `ai/prompts/*.txt` in package data; the existing `pyproject.toml` already does.

**Step 4:** Run the tests; expect 3 passed, then the suite. **Step 5:** Commit `feat: privacy-safe report extraction with verified quotes`.

---

### Task 4: Store and pipeline (`run_insights`)

**Files:** Create `backend/src/investment_agent/insights/store.py` and `backend/src/investment_agent/insights/pipeline.py`. Test: `backend/tests/insights/test_pipeline.py`.

**Step 1: Failing tests** (fake gateway, fake get):

```python
import json
from datetime import date, datetime, timezone
from decimal import Decimal

from investment_agent.ai.openrouter import AIUnavailable, Completion
from investment_agent.insights.pipeline import run_insights
from investment_agent.insights.sources import ReportRef
from investment_agent.insights.store import InsightStore

NOW = datetime(2026, 10, 26, 13, tzinfo=timezone.utc)
REF = ReportRef("acbs", "vi-mo-10-2026", "Cập nhật vĩ mô tháng 10/2026", "https://acbs.com.vn/x", "https://acbs.com.vn/a.pdf", date(2026, 10, 1))
PAGES = ["Tăng trưởng GDP quý III đạt 7,5%.", "Lãi suất thấp hỗ trợ ngành ngân hàng."]
RAW = {"macro_now": {"view": "favourable", "reasons": [{"text": "GDP tốt", "quote": "Tăng trưởng GDP quý III đạt 7,5%", "page": 1}]},
       "macro_outlook": {"view": "neutral", "reasons": []},
       "sectors": [{"sector": "Ngân hàng", "effect": "benefit", "reason": "lãi suất", "quote": "Lãi suất thấp hỗ trợ ngành ngân hàng", "page": 2}]}


class Gateway:
    def __init__(self, fail=None):
        self.calls, self.fail = [], fail

    def complete(self, task, messages, *, job_id, response_format=None, tools=None):
        if self.fail:
            raise AIUnavailable(self.fail)
        self.calls.append(messages)
        return Completion("m/x", "p", json.dumps(RAW, ensure_ascii=False), (), 100, 50, Decimal("0.003"), "reported", "g1", "v")


def deps(tmp_path, gateway):
    return dict(store=InsightStore(tmp_path / "insights"), discover=lambda since: [REF], download=lambda url: b"%PDF",
                pages=lambda data: PAGES, gateway=gateway, sectors=["Ngân hàng", "Dầu khí"], now=NOW, sleep=lambda s: None)


def test_new_report_is_extracted_verified_and_saved_once(tmp_path):
    g = Gateway()
    first = run_insights(**deps(tmp_path, g))
    assert first == {"status": "ok", "processed": ["acbs:vi-mo-10-2026"], "skipped": 0}
    rec = InsightStore(tmp_path / "insights").read("acbs", "vi-mo-10-2026")
    assert rec["status"] == "ok" and rec["insight"]["sectors"][0]["sector"] == "Ngân hàng" and rec["cost_usd"] == "0.003"
    assert run_insights(**deps(tmp_path, g))["processed"] == [] and len(g.calls) == 1


def test_missing_key_or_budget_stops_without_marking_reports_processed(tmp_path):
    for code in ("key_missing", "budget_exceeded"):
        out = run_insights(**deps(tmp_path, Gateway(fail=code)))
        assert out["status"] == f"stopped:{code}" and InsightStore(tmp_path / "insights").read("acbs", "vi-mo-10-2026") is None


def test_report_without_text_is_recorded_and_not_sent_to_ai(tmp_path):
    g = Gateway()
    d = {**deps(tmp_path, g), "pages": lambda data: []}
    run_insights(**d)
    assert InsightStore(tmp_path / "insights").read("acbs", "vi-mo-10-2026")["status"] == "no_text" and g.calls == []
```

**Step 2:** Run it. Expect an ImportError.

**Step 3: Implement**

`store.py`:

```python
"""One JSON per processed report under data/insights/reports."""

import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

_ID = re.compile(r"^[A-Za-z0-9_-]{1,120}$")


class InsightStore:
    def __init__(self, root: Path):
        self.root = Path(root) / "reports"

    def _path(self, source: str, ref_id: str) -> Path:
        if not (_ID.fullmatch(source) and _ID.fullmatch(ref_id)):
            raise ValueError("invalid report id")
        return self.root / f"{source}-{ref_id}.json"

    def read(self, source: str, ref_id: str) -> dict | None:
        p = self._path(source, ref_id)
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    def save(self, record: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        p = self._path(record["source"], record["ref_id"])
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)

    def recent(self, today: date, *, days: int = 60) -> list[dict]:
        cutoff = (today - timedelta(days=days)).isoformat()
        out = [json.loads(p.read_text(encoding="utf-8")) for p in self.root.glob("*.json")] if self.root.is_dir() else []
        return sorted((r for r in out if r["published"] >= cutoff), key=lambda r: r["published"], reverse=True)
```

`pipeline.py`:

```python
"""insights-run: discover new public reports, extract text, ask the model (public text only), keep verified claims."""

import json
from datetime import timedelta

from investment_agent.ai.openrouter import AIUnavailable

from .extract import RESPONSE_FORMAT, build_messages, validate

MAX_REPORTS, FIRST_WINDOW_DAYS, PAUSE = 3, 60, 2.0
STOPPING = {"key_missing", "policy_not_approved", "budget_not_configured", "budget_exceeded", "catalog_stale", "no_eligible_model"}


def run_insights(*, store, discover, download, pages, gateway, sectors, now, sleep) -> dict:
    since = (now - timedelta(days=FIRST_WINDOW_DAYS)).date()
    todo = [r for r in discover(since) if store.read(r.source, r.ref_id) is None][:MAX_REPORTS]
    processed = []
    for i, ref in enumerate(todo):
        if i:
            sleep(PAUSE)
        texts = pages(download(ref.pdf_url))
        record = {"source": ref.source, "ref_id": ref.ref_id, "title": ref.title, "page_url": ref.page_url, "pdf_url": ref.pdf_url,
                  "published": ref.published.isoformat(), "processed_at": now.isoformat(), "telegram_sent": False}
        if not any(t.strip() for t in texts):
            store.save({**record, "status": "no_text", "insight": None, "model": None, "cost_usd": "0"})
            processed.append(f"{ref.source}:{ref.ref_id}")
            continue
        try:
            done = gateway.complete("insights", build_messages(ref.title, texts, sectors), job_id=f"insights-{ref.source}-{ref.ref_id}",
                                    response_format=RESPONSE_FORMAT)
        except AIUnavailable as exc:
            if exc.code in STOPPING:
                return {"status": f"stopped:{exc.code}", "processed": processed, "skipped": len(todo) - len(processed)}
            continue  # transient: retried on the next run
        try:
            insight = validate(json.loads(done.content or "{}"), texts, sectors)
        except ValueError:
            insight = None
        claims = insight and (insight["macro_now"]["reasons"] or insight["macro_outlook"]["reasons"] or insight["sectors"])
        store.save({**record, "status": "ok" if claims else "no_reliable_claims", "insight": insight, "model": done.model,
                    "cost_usd": str(done.cost_usd)})
        processed.append(f"{ref.source}:{ref.ref_id}")
    return {"status": "ok", "processed": processed, "skipped": 0}
```

**Step 4:** Run the tests; expect 3 passed, then the suite. **Step 5:** Commit `feat: insights pipeline with store, budget and key stops`.

---

### Task 5: Local aggregation and linking

**Files:** Create `backend/src/investment_agent/insights/summary.py`. Test: `backend/tests/insights/test_summary.py`.

**Step 1: Failing tests**

```python
from investment_agent.insights.summary import link, summarise


def rec(source, ref, now_view, sectors, published="2026-10-01"):
    return {"source": source, "ref_id": ref, "title": ref, "page_url": f"https://x/{ref}", "published": published, "status": "ok",
            "insight": {"macro_now": {"view": now_view, "reasons": [{"text": f"lý do {ref}", "quote": "q", "page": 1}]},
                        "macro_outlook": {"view": "neutral", "reasons": []}, "sectors": sectors}}


def s(sector, effect):
    return {"sector": sector, "effect": effect, "reason": f"{sector} {effect}", "quote": "q", "page": 2}


def test_summary_counts_views_and_keeps_disagreements_with_their_sources():
    out = summarise([rec("acbs", "a", "favourable", [s("Ngân hàng", "benefit"), s("Dầu khí", "harm")]),
                     rec("worldbank", "w", "unfavourable", [s("Ngân hàng", "harm")]),
                     {"source": "acbs", "ref_id": "z", "status": "no_reliable_claims", "insight": None, "published": "2026-10-02"}])
    assert out["macro_now"]["votes"] == {"favourable": 1, "neutral": 0, "unfavourable": 1} and out["macro_now"]["consensus"] == "mixed"
    bank = next(x for x in out["sectors"] if x["sector"] == "Ngân hàng")
    assert bank["benefit"] == 1 and bank["harm"] == 1 and bank["mixed"] is True and len(bank["claims"]) == 2
    assert out["reports"] == 2  # unreliable reports are not counted


def test_link_adds_watchlist_tickers_valuation_and_held_warnings():
    summary = summarise([rec("acbs", "a", "favourable", [s("Ngân hàng", "benefit"), s("Bất động sản", "harm")])])
    rows = [{"symbol": "BID", "verdict": "cheap"}, {"symbol": "MBB", "verdict": "fair"}, {"symbol": "KDH", "verdict": "cheap"}]
    out = link(summary, sectors={"BID": "Ngân hàng", "MBB": "Ngân hàng", "KDH": "Bất động sản"}, valuation_rows=rows, held={"MBB", "KDH"})
    bank = next(x for x in out["sectors"] if x["sector"] == "Ngân hàng")
    assert bank["tickers"] == [{"symbol": "BID", "verdict": "cheap", "held": False}, {"symbol": "MBB", "verdict": "fair", "held": True}]
    estate = next(x for x in out["sectors"] if x["sector"] == "Bất động sản")
    assert estate["held_warning"] == ["KDH"]
```

**Step 2:** Run it. Expect an ImportError.

**Step 3: Implement**

```python
"""Aggregate verified per-report insights locally (no AI) and link sectors to the owner's watchlist and valuations."""

from collections import defaultdict

VIEWS = ("favourable", "neutral", "unfavourable")


def _macro(records, key):
    votes = {v: 0 for v in VIEWS}
    reasons = []
    for r in records:
        block = r["insight"][key]
        votes[block["view"]] += 1
        reasons += [{**x, "source": r["source"], "title": r["title"], "url": r["page_url"]} for x in block["reasons"]]
    top = [v for v in VIEWS if votes[v] == max(votes.values())]
    consensus = top[0] if len(top) == 1 and max(votes.values()) > 0 else ("mixed" if max(votes.values()) else "none")
    return {"votes": votes, "consensus": consensus, "reasons": reasons}


def summarise(records: list[dict]) -> dict:
    ok = [r for r in records if r.get("status") == "ok" and r.get("insight")]
    sectors = defaultdict(lambda: {"benefit": 0, "harm": 0, "claims": []})
    for r in ok:
        for s in r["insight"]["sectors"]:
            entry = sectors[s["sector"]]
            entry[s["effect"]] += 1
            entry["claims"].append({**s, "source": r["source"], "title": r["title"], "url": r["page_url"]})
    rows = [{"sector": name, **v, "mixed": v["benefit"] > 0 and v["harm"] > 0} for name, v in sectors.items()]
    rows.sort(key=lambda x: (-(x["benefit"] - x["harm"]), x["sector"]))
    return {"reports": len(ok), "macro_now": _macro(ok, "macro_now"), "macro_outlook": _macro(ok, "macro_outlook"), "sectors": rows}


def link(summary: dict, *, sectors: dict[str, str], valuation_rows: list[dict], held: set[str]) -> dict:
    verdict = {r["symbol"]: r["verdict"] for r in valuation_rows}
    by_sector = defaultdict(list)
    for sym, sec in sectors.items():
        by_sector[sec].append(sym)
    out = []
    for row in summary["sectors"]:
        tickers = [{"symbol": t, "verdict": verdict.get(t, "insufficient"), "held": t in held} for t in sorted(by_sector.get(row["sector"], []))]
        warn = [t["symbol"] for t in tickers if t["held"]] if row["harm"] > row["benefit"] else []
        out.append({**row, "tickers": tickers, "held_warning": warn})
    return {**summary, "sectors": out}
```

**Step 4:** Run the tests; expect 2 passed, then the suite. **Step 5:** Commit `feat: local aggregation of report insights linked to watchlist and valuations`.

---

### Task 6: Telegram message per new report

**Files:** Create `backend/src/investment_agent/insights/telegram.py`. Test: `backend/tests/insights/test_insights_telegram.py`.

**Step 1: Failing tests**:
- `render_insight(record, linked_sectors)` returns text that contains:
  - the title;
  - "Vĩ mô hiện tại: Thuận lợi";
  - at most 5 benefit and 5 harm sectors, each with tickers and Vietnamese verdicts (`BID (Rẻ)`) and `⚠ đang nắm` for held tickers in harmed sectors;
  - the source link;
  - "không phải khuyến nghị".
- `send_new(store, sender, settings, render)` sends every `status == "ok"` record with `telegram_sent == False` when `settings.enabled and settings.scheduled_enabled`, then sets `telegram_sent = True`. It sends nothing when scheduled sending is off. Use a fake sender that records `(chat_id, text)` and returns an outcome with `status == "sent"`.

**Step 2:** Run it. Expect an ImportError.

**Step 3: Implement.** Map the views with `{"favourable": "Thuận lợi", "neutral": "Trung tính", "unfavourable": "Bất lợi"}` and the verdicts with `{"cheap": "Rẻ", "fair": "Hợp lý", "expensive": "Đắt", "insufficient": "chưa đủ dữ liệu"}`. Use `split_message` from `notifications.render` for long texts. Mark the record as sent only when every part reports `sent`.

**Step 4:** Run the tests and the suite. **Step 5:** Commit `feat: Telegram summary for each new report`.

---

### Task 7: AI policy, catalog cache, CLI and scheduler

**Files:**
- Create `config/ai-policy.json`.
- Modify `backend/src/investment_agent/ai/catalog.py`: add `load_catalog(path, get, now, max_age_days=7)`, which caches `MODELS_URL` JSON to `data/ai/catalog.json`.
- Modify `backend/src/investment_agent/cli.py`: add `insights-run`.
- Modify `scripts/windows/run-after-close.ps1`.
- Test: `backend/tests/insights/test_cli_insights.py`.

**Step 0 (live, read-only):** fetch `https://openrouter.ai/api/v1/models`. List 2–3 models that support `response_format`, cost no more than $0.50 per million input tokens, and have a context of at least 128k (for example a Gemini Flash and a GPT mini class model). Record their ids and prices in the ledger. The owner approves this pick in the PR.

**`config/ai-policy.json`:**
- copy `ai-policy.example.json`;
- `version: "ai-policy-2026-10-26.1"`, `status: "approved"`, `notice` naming the owner's approval of 2026-10-26 (public report text only, 2 USD/month);
- `tasks.insights = {"models": [<chosen ids>], "required_parameters": ["response_format"], "max_tokens": 2500}`;
- `budget.monthly_usd: "2"`, `per_request_max_usd: "0.20"`, `per_job_max_usd: "0.20"`.

Keep the other tasks, with the models list set to the chosen ids. `load_ai_policy` keeps its example default: the CLI passes the approved path explicitly. The existing report narrator stays unwired; the owner refused portfolio data to AI.

**Step 1: Failing tests:**
- `load_catalog` uses the cache when it is younger than 7 days and refetches otherwise.
- `insights_run(data_dir, get, gateway_factory, now)` returns:
  - 0 with `{"status": "not_configured", "reason": "key_missing"}` when there is no key;
  - otherwise the `run_insights` summary, then the `send_new` summary.

  Use fakes for `get` and the gateway. Sectors come from `load_sectors(data_dir)`; when there are none, it falls back to the ICB names in the watchlist sectors.

**Step 3: Implement** the CLI:
- `insights-run --data-dir`:
  - build `Settings.from_env()`, `load_ai_policy(CONFIG_DIR/"ai-policy.json")`, `SpendLedger(data_dir/"ai"/"spend.sqlite")` and `OpenRouterGateway(..., client=httpx.Client())`;
  - discovery merges `discover_acbs` and `discover_worldbank`;
  - download uses httpx with the project User-Agent, follows redirects and refuses files over 40 MB;
  - pages come from `extract_pages`;
  - Telegram uses the existing `TelegramSender` when `TELEGRAM_BOT_TOKEN` is set, with the notification settings read from Firestore as `scheduled-run` does.
- Add to `run-after-close.ps1` after `macro-sync`:
  ```powershell
  # Public research reports (ACBS, World Bank): AI reads public text only; at most 3 new reports per run.
  $ins = & $python -W ignore -m investment_agent.cli insights-run --data-dir $data 2>$null
  "$(Get-Date -Format o) insights-run exit=$LASTEXITCODE $ins" | Add-Content -LiteralPath $log -Encoding UTF8
  ```

**Step 4:** Run the tests and the suite. The script must parse with 0 errors. **Step 5:** Commit `feat: insights-run with approved AI policy, catalog cache and schedule`.

---

### Task 8: API `GET /internal/insights`

**Files:**
- Create `backend/src/investment_agent/api/routes/insights.py`.
- Modify `app.py` (register the router) and `python-proxy.ts` (add the area `insights`).
- Test: `backend/tests/api/test_insights_route.py`.

**Steps:** The failing test seeds two records in `tmp_path/insights` and fundamentals for one ticker (reuse the Task 5 fixture shape from `test_fairvalue_route.py`). It asserts that the response has:
- `summary.reports == 2`;
- linked sectors with tickers;
- the latest 10 `reports` with title, source, published date, status and link;
- `ssi: []`, because the route never fetches; SSI titles are cached by `insights-run` into `data/insights/ssi.json`;
- `ai_configured`, true when `OPENROUTER_API_KEY` is set.

The response never contains `pdf_url` bytes or full texts. Implement it by reusing `held_tickers`, `load_sectors` and the `/fairvalue` board computation: extract a helper `fair_value_rows(request)` from `fairvalue.py` and use it in both routes. Then run the suite and commit `feat: insights API`.

Also extend Task 7's `insights_run` to write `data/insights/ssi.json` with `ssi_titles(get, limit=10)` on each run, ignoring fetch errors.

---

### Task 9: Page "Nhận định"

**Files:**
- Create `apps/web/src/components/insights-view.tsx` and `apps/web/src/app/(private)/insights/page.tsx`.
- Modify the nav (`{ href: "/insights", label: "Nhận định", icon: Newspaper }` after "Vĩ mô"), `globals.css` and `tests/e2e/fixture_backend.py` (seed two insight records and one SSI title).
- Test: `tests/e2e/insights.spec.ts`.

**Layout:**
1. A notice: "Tổng hợp từ báo cáo công khai (ACBS, World Bank); AI chỉ đọc nội dung báo cáo; không phải khuyến nghị".
2. **Vĩ mô:** two cards, *Hiện tại* and *6–12 tháng*. Each shows the consensus pill (Thuận lợi green, Trung tính grey, Bất lợi red, Chưa thống nhất amber), the vote counts and the reasons with their source and a link.
3. **Ngành:** a table with Ngành, Hưởng lợi, Bất lợi, Lý do (first claim, plus "Xem thêm"), and Mã theo dõi. Mã theo dõi lists tickers with verdict pills; held tickers are bold, and harmed held tickers get a ⚠.
4. **Báo cáo đã đọc:** a list with source, date, title, status and link.
5. **Tiêu đề mới từ SSI:** a list of links.
6. When `ai_configured` is false, show the banner "Chưa cấu hình AI: thêm OPENROUTER_API_KEY vào .env.local".

**e2e tests** (RED first):
- the macro consensus and a reason are visible;
- the bank row shows `BID` with "Rẻ";
- the warning ⚠ appears for a held ticker in a harmed sector;
- the SSI title is listed;
- no horizontal scroll at 375px, using the same scroller check as `fair-value.spec.ts`.

Then run `verify.ps1` and commit `feat: Nhận định page`.

---

### Task 10: PR and live run (owner-gated)

1. Open the PR. List the models chosen with their prices for the owner's approval, the privacy guarantee and its test, the sources and their limits (World Bank's newest matching document was 2025-03), and the tests with their RED runs.
2. After the merge: install `pypdf` in the main `.venv`, rebuild and restart.
3. Wait for the owner to add `OPENROUTER_API_KEY` and set a credit limit on the key. Then run `insights-run --data-dir data` once and spot-check 2 quotes against the ACBS PDF. Report the cost from the spend ledger.
