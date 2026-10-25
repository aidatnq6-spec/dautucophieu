from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.ledger import LedgerError, LedgerEvent, parse_events, replay
from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import InvalidRecord, RepositoryUnavailable, VersionConflict

from ..auth import require_owner
from .common import WRITE_ERRORS, error, read_current, read_version, unavailable, write_error

router = APIRouter(prefix="/internal/ledger")
# One aggregate record: its version covers the whole ledger, so order and inventory
# rules are checked against exactly the events the CAS write replaces.
COLLECTION, RECORD = "ledger_events", "main"


class AppendRequest(ContractModel):
    event: LedgerEvent
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(version, events, *, stale=False):
    return {"version": version, "events": [e.model_dump(mode="json") for e in events],
            "state": replay(events).model_dump(mode="json"), "stale": stale}


def _events(record):
    return parse_events(record.payload["events"]) if record else []


@router.get("")
def current(request: Request):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record, stale = read_current(repo, owner, COLLECTION, RECORD)
    except RepositoryUnavailable:
        return unavailable()
    return _view(record.version if record else 0, _events(record), stale=stale)


@router.post("/events")
def append(request: Request, body: AppendRequest):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    # Build on the exact version the client saw: a retry then reproduces the original
    # payload and the repository returns the committed revision instead of appending twice.
    try:
        head = read_version(repo, owner, COLLECTION, RECORD, None)
        base = read_version(repo, owner, COLLECTION, RECORD, body.expected_version) if body.expected_version else None
    except RepositoryUnavailable:
        return unavailable()
    current = head.version if head else 0
    if body.expected_version > current or (body.expected_version and base is None):
        return write_error(VersionConflict())
    events = [*_events(base), body.event]
    if body.expected_version == current:
        try:
            replay(events)
        except LedgerError as exc:
            return error(422, f"ledger_{exc.code}", "Giao dịch mâu thuẫn với sổ hiện tại (số lượng, tiền, thứ tự hoặc trùng mã).")
    # Behind the head: only an identical retry succeeds; anything else is a VersionConflict in the repository.
    try:
        saved = repo.write(owner, COLLECTION, RECORD, {"schema_version": "1", "events": [e.model_dump(mode="json") for e in events]},
                           expected_version=body.expected_version, request_id=body.request_id)
    except InvalidRecord:
        return error(422, "ledger_too_large", "Sổ vượt giới hạn lưu một bản ghi; cần tách kỳ sổ.")
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return _view(saved.version, _events(saved))
