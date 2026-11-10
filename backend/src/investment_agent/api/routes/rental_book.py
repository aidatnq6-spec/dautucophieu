"""Sổ cho thuê căn hộ on Hồ sơ & rủi ro: rooms, tenants, leases and the rent received. Saved as one book."""

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.rental_book import RentalBook, book_view
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.rental_alerts import RECORD
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, now, unavailable, write_error

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class BookRequest(RentalBook):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    stored = read_version(repo, owner, *RECORD, None)
    book = RentalBook.model_validate(stored.payload) if stored else RentalBook()
    return {"version": stored.version if stored else 0, "book": book.model_dump(mode="json"), "view": book_view(book, today=now(request).astimezone(VN).date())}


@router.get("/rental-book")
def get_book(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/rental-book")
def put_book(request: Request, body: BookRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    payload = RentalBook.model_validate(body.model_dump(exclude={"expected_version", "request_id"})).model_dump(mode="json")
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
