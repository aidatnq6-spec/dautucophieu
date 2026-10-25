from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.ledger import LedgerError, LedgerEvent, parse_events, replay
from investment_agent.domain.models import ContractModel
from investment_agent.domain.reconciliation import Amendment, Change, apply_amendments, parse_amendments
from investment_agent.repositories.personal import InvalidRecord, RepositoryUnavailable, VersionConflict

from ..auth import require_owner
from .common import WRITE_ERRORS, error, read_current, read_version, unavailable, write_error

router = APIRouter(prefix="/internal/ledger")
# One aggregate record: its version covers the whole ledger, so order and inventory
# rules are checked against exactly the events the CAS write replaces.
COLLECTION, RECORD = "ledger_events", "main"


class _Mutation(ContractModel):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class AppendRequest(_Mutation):
    event: LedgerEvent


class AmendRequest(_Mutation):
    amendment: Amendment


class LedgerBook:
    """Stored payload: original events, ordered amendments and the change log."""

    def __init__(self, record):
        payload = record.payload if record else {}
        self.events = parse_events(payload.get("events", []))
        self.amendments = parse_amendments(payload.get("amendments", []))
        self.changes = [Change.model_validate(c) for c in payload.get("changes", [])]

    def effective(self):
        return apply_amendments(self.events, self.amendments)

    def payload(self):
        return {"schema_version": "2", "events": [e.model_dump(mode="json") for e in self.events],
                "amendments": [a.model_dump(mode="json") for a in self.amendments],
                "changes": [c.model_dump(mode="json") for c in self.changes]}


def _view(version, book, *, stale=False):
    amended = book.effective()
    return {"version": version, "events": [e.model_dump(mode="json") for e in amended.events],
            "original_events": [e.model_dump(mode="json") for e in book.events],
            "audit": [a.model_dump(mode="json") for a in amended.audit],
            "changes": [c.model_dump(mode="json") for c in book.changes],
            "state": replay(list(amended.events)).model_dump(mode="json"), "stale": stale}


def _rejected(exc: LedgerError):
    return error(422, f"ledger_{exc.code}", "Thay đổi mâu thuẫn với sổ hiện tại (số lượng, tiền, thứ tự, trùng mã hoặc sửa đổi không hợp lệ).")


def _mutate(request: Request, body: _Mutation, change):
    """change(book) mutates the book and returns the affected_from date."""
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    # Build on the exact version the client saw: a retry then reproduces the original
    # payload and the repository returns the committed revision instead of applying twice.
    try:
        head = read_version(repo, owner, COLLECTION, RECORD, None)
        base = read_version(repo, owner, COLLECTION, RECORD, body.expected_version) if body.expected_version else None
    except RepositoryUnavailable:
        return unavailable()
    current = head.version if head else 0
    if body.expected_version > current or (body.expected_version and base is None):
        return write_error(VersionConflict())
    book = LedgerBook(base)
    try:
        affected_from = change(book)
        book.changes.append(Change(ledger_version=body.expected_version + 1, affected_from=affected_from))
        if body.expected_version == current:
            replay(list(book.effective().events))
    except LedgerError as exc:
        if body.expected_version == current:
            return _rejected(exc)
        return write_error(VersionConflict())
    # Behind the head: only an identical retry succeeds; anything else is a VersionConflict in the repository.
    try:
        saved = repo.write(owner, COLLECTION, RECORD, book.payload(), expected_version=body.expected_version, request_id=body.request_id)
    except InvalidRecord:
        return error(422, "ledger_too_large", "Sổ vượt giới hạn lưu một bản ghi; cần tách kỳ sổ.")
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return _view(saved.version, LedgerBook(saved))


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
    return _view(record.version if record else 0, LedgerBook(record), stale=stale)


@router.post("/events")
def append(request: Request, body: AppendRequest):
    def change(book):
        book.events.append(body.event)
        return body.event.effective_at
    return _mutate(request, body, change)


@router.post("/amendments")
def amend(request: Request, body: AmendRequest):
    def change(book):
        book.amendments.append(body.amendment)
        return book.effective().audit[-1].affected_from
    return _mutate(request, body, change)
