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
SSI_PAGES = {"vĩ mô": "https://www.ssi.com.vn/khach-hang-ca-nhan/bao-cao-vi-mo",
             "ngành": "https://www.ssi.com.vn/khach-hang-ca-nhan/bao-cao-nganh",
             "chiến lược": "https://www.ssi.com.vn/khach-hang-ca-nhan/bao-cao-chien-luoc"}
_ACBS_LINK = re.compile(r'<a[^>]+href="([^"]*/trung-tam-phan-tich/chi-tiet/([a-z0-9-]+))"[^>]*>(.*?)</a>', re.S)
_ACBS_PDF = re.compile(r'href="([^"]*acbsmedia/(\d{4})/(\d{2})/[^"]+\.pdf)"', re.I)
_ACBS_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
# ETF portfolio forecasts and index-rule notes are not macro or sector views.
_ACBS_SKIP = re.compile(r"(?:^|-)etf(?:-|$)|quy-tac-chi-so")
# One SSI list item: title, then date, then the (login-gated) download link.
_SSI_ITEM = re.compile(r'class="titlePost"[^>]*>(.*?)</a>.*?<span>\s*(\d{2})/(\d{2})/(\d{4})\s*</span>.*?'
                       r'href="((?:https://www\.ssi\.com\.vn)?/analysis-center/report/download/([a-z0-9-]+))"', re.S)
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


def discover_acbs(get, *, since: date, known=lambda slug: False) -> list[ReportRef]:
    """known(slug) True skips the detail-page fetch for reports already processed."""
    refs, seen = [], set()
    for m in _ACBS_LINK.finditer(get(ACBS_LIST)):
        page_url, slug, title = urljoin(ACBS_LIST, m.group(1)), m.group(2), _text(m.group(3))
        if slug in seen or known(slug) or _ACBS_SKIP.search(slug):
            continue
        seen.add(slug)
        detail = get(page_url)
        pdf = _ACBS_PDF.search(detail)
        if not pdf:
            continue
        published = date(int(pdf.group(2)), int(pdf.group(3)), 1)
        h1 = _ACBS_H1.search(detail)
        title = (_text(h1.group(1)) if h1 else "") or title  # list anchors carry only the category label
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
        for m in _SSI_ITEM.finditer(get(url)):
            full = urljoin(url, m.group(5))
            if full in seen:
                continue
            seen.add(full)
            title = _text(m.group(1)) or m.group(6).replace("-", " ").capitalize()
            out.append({"title": title, "kind": kind, "date": f"{m.group(4)}-{m.group(3)}-{m.group(2)}", "url": full})
    return sorted(out, key=lambda x: x["date"], reverse=True)[:limit]
