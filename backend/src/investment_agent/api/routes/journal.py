"""Nhật ký đầu tư: reason and emotion behind each decision, the context captured on save, and appended notes (never edits)."""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.journal import JournalEntry
from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.holdings_view import held_from_repo
from investment_agent.services.journal import EntryNotFound, append_entry, append_note, capture_context, change, read_journal
from investment_agent.services.records import portfolio_settings

from ..auth import require_owner
from .common import WRITE_ERRORS, error, unavailable, write_error
from .common import now as request_now

router = APIRouter(prefix="/internal")
REQUEST_ID = r"^[A-Za-z0-9_-]{1,64}$"


class EntryRequest(ContractModel):
    symbol: str = Field(min_length=2, max_length=10)
    kind: Literal["buy", "sell", "hold"]
    reason: str = Field(default="", max_length=4000)
    emotion: Literal["calm", "excited", "fomo", "anxious", "panic", "regret"] | None = None
    emotion_note: str = Field(default="", max_length=500)
    ledger_event_id: str | None = Field(default=None, max_length=128)
    request_id: str = Field(pattern=REQUEST_ID)


class NoteRequest(ContractModel):
    text: str = Field(min_length=1, max_length=2000)
    request_id: str = Field(pattern=REQUEST_ID)


@router.get("/journal")
def get_journal(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        entries, version = read_journal(repo, owner)
        settings, _ = portfolio_settings(repo, owner)
        held = sorted(held_from_repo(repo, owner))
    except RepositoryUnavailable:
        return unavailable()
    market, rows = request.app.state.market, []
    for e in reversed(entries):
        point = market.price(e.symbol)
        current = point.price if point is not None else None
        rows.append({**e.model_dump(mode="json"), "current_price": str(current) if current is not None else None,
                     "change": change(e.context.get("price"), current)})
    return {"version": version, "threshold": str(settings.journal_review_threshold), "held": held, "entries": rows}


@router.post("/journal")
def post_entry(request: Request, body: EntryRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    symbol, today = body.symbol.strip().upper(), request_now(request).date()
    try:
        context = capture_context(symbol, market=request.app.state.market, data_dir=request.app.state.data_dir, repo=repo, owner=owner, today=today)
        entry = JournalEntry(entry_id=body.request_id, symbol=symbol, kind=body.kind, created_on=today, reason=body.reason.strip(),
                             emotion=body.emotion, emotion_note=body.emotion_note.strip(), context=context, ledger_event_id=body.ledger_event_id)
    except ValueError:
        return error(422, "invalid_entry", "Mã hoặc nội dung nhật ký không hợp lệ.")
    except RepositoryUnavailable:
        return unavailable()
    try:
        saved = append_entry(repo, owner, entry, request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return saved.model_dump(mode="json")


@router.post("/journal/{entry_id}/notes")
def post_note(request: Request, entry_id: str, body: NoteRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        saved = append_note(repo, owner, entry_id, text=body.text.strip(), on=request_now(request).date(), request_id=body.request_id)
    except EntryNotFound:
        return error(404, "entry_not_found", "Không tìm thấy mục nhật ký.")
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return saved.model_dump(mode="json")
