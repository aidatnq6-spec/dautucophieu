"""Hỏi AI về tài liệu công khai (C5): fetch one public document, keep its text, ask the model under the approved policy, check what
comes back (ai/doc_ask). Only the ticker, a screened question and passages of the document go out; the owner's own row names are
read here to screen the question and never leave this machine."""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Callable
from urllib import robotparser
from urllib.parse import urlsplit

from investment_agent.ai.doc_ask import (
    Blocked, Unverified, check_answer, check_rows, qa_messages, rr_messages, screen_question, select_passages,
)

DOCS_DIR = "ai-docs"
MAX_PAGES, MAX_BYTES, MAX_SECONDS = 300, 20 * 1024 * 1024, 120
USER_AGENT = "investment-agent/0.1 (personal use)"
RR_QUERY = ("phải thu bên liên quan giao dịch số dư các bên liên quan công ty liên kết trả trước cho người bán nhà cung cấp "
            "related parties receivables advances to suppliers")
JSON_FORMAT = {"type": "json_object"}


class DocError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def personal_names(repo, owner) -> set[str]:
    """Names the owner gave their own rows (Sổ tài sản: accounts, bonds, gold, crypto); used to screen questions, never sent."""
    from investment_agent.services.deposit_book import read_book
    try:
        book, _ = read_book(repo, owner)
    except Exception:
        return set()
    if book is None:
        return set()
    return {r.name for rows in (book.accounts, book.bonds, book.gold, book.crypto) for r in rows}


def _cache_path(data_dir: Path, url: str) -> Path:
    return Path(data_dir) / DOCS_DIR / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.json"


def document_pages(data_dir: Path, url: str, *, fetch: Callable[[str], list[str]]) -> list[str]:
    """The document's text by page, from the cache or fetched once; a document without text is refused (no OCR)."""
    path = _cache_path(data_dir, url)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))["pages"]
    pages = fetch(url)
    if not any(p.strip() for p in pages):
        raise DocError("no_text", "Không trích được văn bản từ tài liệu (có thể là bản scan); phần mềm không OCR.")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"url": url, "fetched_at": datetime.now(timezone.utc).isoformat(), "pages": pages}, ensure_ascii=False),
                   encoding="utf-8")
    os.replace(tmp, path)
    return pages


def live_fetch(url: str) -> list[str]:
    """Download a public document politely (robots.txt, no redirects, size and time caps) and extract its text."""
    import httpx

    from investment_agent.insights.download import fetch_pdf
    from investment_agent.insights.pdf import extract_pages
    parts = urlsplit(url)
    robots = robotparser.RobotFileParser()
    try:
        with httpx.Client(timeout=15, headers={"User-Agent": USER_AGENT}) as c:
            r = c.get(f"{parts.scheme}://{parts.netloc}/robots.txt")
            robots.parse(r.text.splitlines() if r.status_code == 200 else [])
    except httpx.HTTPError:
        robots.parse([])
    if not robots.can_fetch(USER_AGENT, url):
        raise DocError("robots_disallow", "robots.txt của trang này không cho đọc tự động tài liệu.")
    with httpx.Client(follow_redirects=False, timeout=httpx.Timeout(60, connect=15), headers={"User-Agent": USER_AGENT}) as c:
        try:
            data = fetch_pdf(c, url, max_bytes=MAX_BYTES, max_seconds=MAX_SECONDS)
        except httpx.HTTPStatusError as exc:
            if 300 <= exc.response.status_code < 400:
                raise DocError("redirect", "Link chuyển hướng sang chỗ khác: hãy dán link cuối cùng của tệp.") from exc
            raise DocError("download_failed", f"Không tải được tài liệu (mã {exc.response.status_code}).") from exc
        except (httpx.HTTPError, ValueError, TimeoutError) as exc:
            raise DocError("download_failed", "Không tải được tài liệu (quá lớn, quá chậm hoặc lỗi mạng).") from exc
    if not data.startswith(b"%PDF"):
        raise DocError("not_pdf", "Link không phải tệp PDF.")
    return extract_pages(data, max_pages=MAX_PAGES)


def month_spend(data_dir: Path, now: datetime, monthly: Decimal) -> dict:
    from investment_agent.ai.budget import SpendLedger
    month = now.strftime("%Y-%m")
    path = Path(data_dir) / "ai" / "spend.sqlite"
    used = Decimal(0)
    if path.is_file():
        rows = [r for r in SpendLedger(path)._rows("month = ?", (month,)) if r[0] != "released"]
        used = SpendLedger._counted(rows)
    return {"month": month, "used_usd": str(used.quantize(Decimal("0.0001"), ROUND_HALF_UP)), "monthly_usd": str(monthly)}


def ask(gateway, *, symbol: str, question: str, pages: list[str], personal: set[str], tickers: set[str]) -> dict:
    """Blocked raises before anything is sent; an answer that fails its check gets one repair, then is withheld."""
    q = screen_question(question, symbol=symbol, personal_names=personal, tickers=tickers)
    passages = select_passages(pages, q)
    if not passages:
        return {"status": "no_passages", "answer": None, "pages": [], "cost_usd": "0"}
    messages, cost = qa_messages(symbol, q, passages), Decimal(0)
    for attempt in range(2):
        done = gateway.complete("doc_qa", messages, job_id=f"doc-qa-{uuid.uuid4().hex[:12]}", response_format=JSON_FORMAT)
        cost += done.cost_usd
        try:
            return {"status": "ok", **check_answer(done.content, passages), "cost_usd": str(cost)}
        except Unverified as exc:
            messages = [*messages, {"role": "assistant", "content": done.content or ""},
                        {"role": "user", "content": f"Câu trả lời chưa đạt kiểm tra ({exc.code}). Chỉ dùng số và trang có trong các đoạn đã cho; "
                                                    "trả lại đúng JSON."}]
    return {"status": "unverified", "answer": None, "pages": [], "cost_usd": str(cost)}


def propose_related(gateway, *, symbol: str, year: str, pages: list[str]) -> dict:
    passages = select_passages(pages, RR_QUERY)
    if not passages:
        return {"status": "no_passages", "rows": [], "dropped": [], "cost_usd": "0"}
    done = gateway.complete("notes_extract", rr_messages(symbol, year, passages), job_id=f"notes-{uuid.uuid4().hex[:12]}",
                            response_format=JSON_FORMAT)
    try:
        rows, dropped = check_rows(done.content, passages, document_text=" ".join(pages))
    except Unverified as exc:
        return {"status": "unverified", "reason": exc.code, "rows": [], "dropped": [], "cost_usd": str(done.cost_usd)}
    return {"status": "ok", "rows": rows, "dropped": dropped, "cost_usd": str(done.cost_usd)}


__all__ = ["Blocked", "DocError", "ask", "document_pages", "live_fetch", "month_spend", "personal_names", "propose_related"]
