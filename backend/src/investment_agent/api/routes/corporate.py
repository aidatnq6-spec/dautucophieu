"""Cổ tức và quyền on Danh mục & Giao dịch: ledger lines drafted from the Lịch sự kiện, suggestions the owner set aside, and the
taxes and fees recorded each year."""

from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.corporate_suggestions import suggestions, yearly_costs
from investment_agent.domain.models import ContractModel
from investment_agent.market.corporate_events import EventStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import LedgerBook, read_version
from investment_agent.services.weekly_brief import VN

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal/ledger")
DISMISSED = ("settings", "corporate_dismissed")


def _dismissed(repo, owner) -> tuple[list[str], int]:
    record = read_version(repo, owner, *DISMISSED, None)
    return (list(record.payload.get("ids", [])), record.version) if record else ([], 0)


def _view(request: Request, repo, owner, dismissed: list[str], version: int) -> dict:
    events = list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)
    symbols = sorted({e.security_id for e in events if getattr(e, "security_id", None)}
                     | {p.security_id for e in events for p in getattr(e, "positions", ())})
    corporate = EventStore(Path(request.app.state.data_dir)).events(symbols) if request.app.state.data_dir is not None else []
    today = now(request).astimezone(VN).date()
    by_id = {e["id"]: e for e in corporate}
    return {"version": version, "suggestions": suggestions(events, corporate, today=today, dismissed=set(dismissed)), "costs": yearly_costs(events),
            "dismissed": [{"id": i, "symbol": by_id[i]["symbol"], "title": by_id[i]["title"], "exright": by_id[i]["exright"]} for i in dismissed if i in by_id]}


@router.get("/corporate")
def corporate(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner, *_dismissed(repo, owner))
    except RepositoryUnavailable:
        return unavailable()


class Dismiss(ContractModel):
    action: str = Field(pattern=r"^(dismiss|restore)$")
    id: str = Field(min_length=1, max_length=128)
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


@router.put("/corporate")
def corporate_dismiss(request: Request, body: Dismiss):
    """Set a suggestion aside (the papers differ, or it does not apply) or bring it back."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        ids, _ = _dismissed(repo, owner)
        ids = [i for i in ids if i != body.id] + ([body.id] if body.action == "dismiss" else [])
        if len(ids) > 500:
            return error(422, "too_many", "Đã bỏ qua quá nhiều gợi ý.")
        record = repo.write(owner, *DISMISSED, {"ids": ids}, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner, ids, record.version)
    except WRITE_ERRORS as exc:
        return write_error(exc)
