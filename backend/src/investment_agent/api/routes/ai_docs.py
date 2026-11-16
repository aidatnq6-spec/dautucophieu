"""Hỏi AI về tài liệu công khai (C5) on the ticker page: a question about one public document of the page's ticker, and rows proposed for
Phải thu bên liên quan from a company's notes (shown to the owner, never saved by the model). The owner approved on 16/11/2026 that the
ticker, a screened question and passages of the document may go to the model; nothing of the owner's own goes out."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.ai.doc_ask import Blocked
from investment_agent.domain.bank_figures import UnsafeUrl, check_public_https
from investment_agent.domain.models import ContractModel
from investment_agent.market.watchlist import load_watchlist
from investment_agent.services import doc_ai

from ..auth import require_owner
from .common import error, unavailable

router = APIRouter(prefix="/internal/ai-docs")
BLOCKED = {"empty": "Hãy nhập câu hỏi.", "too_long": "Câu hỏi dài quá 300 ký tự.",
           "amount": "Câu hỏi có số tiền: phần mềm không gửi số tiền cho AI. Hãy hỏi mà không ghi số.",
           "personal": "Câu hỏi nói về bạn hoặc danh mục của bạn: phần mềm không gửi những điều này cho AI. Hãy hỏi về tài liệu thôi.",
           "personal_name": "Câu hỏi có tên một sổ hay tài khoản của bạn: phần mềm không gửi cho AI.",
           "other_ticker": "Câu hỏi nhắc mã khác: chỉ hỏi về mã của trang này."}
UNAVAILABLE = {"key_missing": "Chưa có key OpenRouter (Cài đặt).", "budget_exceeded": "Đã hết ngân sách AI tháng này.",
               "catalog_stale": "Bảng giá mô hình đã cũ; thử lại sau.", "no_eligible_model": "Không có mô hình nào đủ điều kiện chính sách.",
               "request_over_budget": "Tài liệu quá dài cho mức chi tối đa mỗi lần hỏi.", "policy_not_approved": "Chính sách AI chưa được duyệt."}


class AskRequest(ContractModel):
    url: str = Field(max_length=500)
    question: str = Field(max_length=1000)


class RelatedRequest(ContractModel):
    url: str = Field(max_length=500)
    year: str = Field(pattern=r"^20\d{2}$")


def _gateway(request: Request, data_dir: Path):
    gateway = getattr(request.app.state, "ai_gateway", None)
    if gateway is not None:
        return gateway, None
    import httpx

    from investment_agent.ai.budget import SpendLedger
    from investment_agent.ai.catalog import load_catalog
    from investment_agent.ai.openrouter import OpenRouterGateway, load_ai_policy
    from investment_agent.domain.pinned import CONFIG_DIR
    from investment_agent.settings import Settings
    settings = Settings.from_env()
    if not settings.openrouter_api_key:
        return None, "key_missing"

    def get(url: str) -> str:
        return httpx.get(url, timeout=30).raise_for_status().text
    try:
        catalog = load_catalog(data_dir / "ai" / "catalog.json", get, now=datetime.now(timezone.utc))
    except Exception:
        return None, "catalog_stale"
    return OpenRouterGateway(settings, load_ai_policy(CONFIG_DIR / "ai-policy.json"), catalog, SpendLedger(data_dir / "ai" / "spend.sqlite"),
                             client=httpx.Client()), None


def _monthly() -> object:
    from investment_agent.ai.openrouter import load_ai_policy
    from investment_agent.domain.pinned import CONFIG_DIR
    approved = CONFIG_DIR / "ai-policy.json"
    return load_ai_policy(approved if approved.is_file() else CONFIG_DIR / "ai-policy.example.json").budget.monthly_usd


def _prepare(request: Request, symbol: str, url: str):
    """(symbol, data_dir, pages) or an error response."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    data_dir, symbol = Path(data_dir), symbol.upper()
    watched = load_watchlist(data_dir).symbols
    if symbol not in watched:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    try:
        check_public_https(url.strip(), resolve=getattr(request.app.state, "ai_resolve", None))
    except UnsafeUrl as exc:
        return error(422, "unsafe_url", f"{exc} Chỉ nhận link https công khai của tài liệu.")
    try:
        pages = doc_ai.document_pages(data_dir, url.strip(), fetch=getattr(request.app.state, "ai_document", None) or doc_ai.live_fetch)
    except doc_ai.DocError as exc:
        return error(422, exc.code, exc.message)
    return symbol, data_dir, pages, set(watched)


def _run(request: Request, data_dir: Path, work) -> dict:
    from investment_agent.ai.openrouter import AIUnavailable
    gateway, why = _gateway(request, data_dir)
    if gateway is None:
        return error(503, why, UNAVAILABLE.get(why, "AI chưa dùng được."))
    try:
        out = work(gateway)
    except AIUnavailable as exc:
        code = str(exc)
        return error(503, code, UNAVAILABLE.get(code, "AI chưa dùng được lúc này."))
    clock = request.app.state.clock
    now = datetime.fromtimestamp(clock(), timezone.utc)
    return {**out, "spend": doc_ai.month_spend(data_dir, now, _monthly())}


@router.post("/{symbol}/ask")
def ask(symbol: str, request: Request, body: AskRequest):
    from investment_agent.ai.doc_ask import screen_question
    owner, repo, data_dir = require_owner(request), request.app.state.personal_repository, request.app.state.data_dir
    personal = doc_ai.personal_names(repo, owner) if repo is not None else set()
    watched = set(load_watchlist(Path(data_dir)).symbols) if data_dir is not None else set()
    try:  # first of all: a blocked question fetches nothing and sends nothing
        screen_question(body.question, symbol=symbol.upper(), personal_names=personal, tickers=watched)
    except Blocked as exc:
        return error(422, f"blocked_{exc.reason}", BLOCKED[exc.reason])
    ready = _prepare(request, symbol, body.url)
    if not isinstance(ready, tuple):
        return ready
    sym, data_dir, pages, tickers = ready
    out = _run(request, data_dir, lambda gw: doc_ai.ask(gw, symbol=sym, question=body.question, pages=pages, personal=personal, tickers=tickers))
    return {**out, "url": body.url.strip()} if isinstance(out, dict) else out


@router.post("/{symbol}/related-receivables")
def related(symbol: str, request: Request, body: RelatedRequest):
    ready = _prepare(request, symbol, body.url)
    if not isinstance(ready, tuple):
        return ready
    sym, data_dir, pages, _ = ready
    out = _run(request, data_dir, lambda gw: doc_ai.propose_related(gw, symbol=sym, year=body.year, pages=pages))
    return {**out, "url": body.url.strip()} if isinstance(out, dict) else out


@router.get("/status")
def status(request: Request):
    require_owner(request)
    from investment_agent.settings import Settings
    data_dir = request.app.state.data_dir
    now = datetime.fromtimestamp(request.app.state.clock(), timezone.utc)
    return {"key_configured": bool(Settings.from_env().openrouter_api_key) or getattr(request.app.state, "ai_gateway", None) is not None,
            "spend": doc_ai.month_spend(Path(data_dir), now, _monthly()) if data_dir else None}
