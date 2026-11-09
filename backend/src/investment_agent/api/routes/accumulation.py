"""Kế hoạch tích sản on Hồ sơ & rủi ro. A purchase recorded here does not change Sổ tài sản or Tháp tài sản."""

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.accumulation import Accumulation
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.accumulation import RECORD, accumulation_view
from investment_agent.services.deposit_book import book_quotes

from ..auth import require_owner
from .common import WRITE_ERRORS, now, unavailable, write_error

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class AccumulationRequest(Accumulation):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    return accumulation_view(repo, owner, quotes=book_quotes(request.app.state.data_dir), today=now(request).astimezone(VN).date())


@router.get("/accumulation")
def get_accumulation(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/accumulation")
def put_accumulation(request: Request, body: AccumulationRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    payload = Accumulation.model_validate(body.model_dump(exclude={"expected_version", "request_id"})).model_dump(mode="json")
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
