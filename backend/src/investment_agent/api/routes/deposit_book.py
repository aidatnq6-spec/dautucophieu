"""Sổ tài sản on Hồ sơ & rủi ro: cash accounts, term deposits, bonds, gold and crypto, saved as one book, with the maturity calendar
and cash now."""

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.deposit_book import DepositBook
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.deposit_book import RECORD, book_quotes, book_view
from investment_agent.services.equity_budget import protected_deductions

from ..auth import require_owner
from .common import WRITE_ERRORS, now, unavailable, write_error

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class BookRequest(DepositBook):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    reserve, from_profile, _ = protected_deductions(repo, owner)
    return book_view(repo, owner, reserve=reserve, profile_reserve=from_profile, quotes=book_quotes(request.app.state.data_dir),
                     today=now(request).astimezone(VN).date())


@router.get("/deposit-book")
def get_book(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/deposit-book")
def put_book(request: Request, body: BookRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    payload = DepositBook.model_validate(body.model_dump(exclude={"expected_version", "request_id"})).model_dump(mode="json")
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
