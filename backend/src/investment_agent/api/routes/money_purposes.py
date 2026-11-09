"""Mục đích từng khoản tiền on Hồ sơ & rủi ro. Reads Sổ tài sản, never feeds it or Tháp tài sản."""

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.deposit_book import DepositBook
from investment_agent.domain.money_purposes import MoneyPurposes, book_rows, purpose_view
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.deposit_book import book_quotes, read_book
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, now, unavailable, write_error

router = APIRouter(prefix="/internal")
RECORD = ("settings", "money_purposes")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class PurposesRequest(MoneyPurposes):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    stored = read_version(repo, owner, *RECORD, None)
    data = MoneyPurposes.model_validate(stored.payload) if stored else MoneyPurposes()
    rows = book_rows(read_book(repo, owner)[0] or DepositBook(), book_quotes(request.app.state.data_dir), today=now(request).astimezone(VN).date())
    return {"version": stored.version if stored else 0, "data": data.model_dump(mode="json"), "rows": rows, "view": purpose_view(rows, data)}


@router.get("/money-purposes")
def get_purposes(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/money-purposes")
def put_purposes(request: Request, body: PurposesRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    payload = MoneyPurposes.model_validate(body.model_dump(exclude={"expected_version", "request_id"})).model_dump(mode="json")
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
