"""Giỏ chiến lược on the Danh mục page: the owner's baskets of holding periods and what each made."""

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.baskets import RECORD, TradeBaskets, baskets_for
from investment_agent.services.weekly_brief import VN

from ..auth import require_owner
from .common import WRITE_ERRORS, now, unavailable, write_error

router = APIRouter(prefix="/internal")


class BasketsRequest(TradeBaskets):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    return baskets_for(repo, owner, request.app.state.market, request.app.state.data_dir, today=now(request).astimezone(VN).date())


@router.get("/baskets")
def get_baskets(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/baskets")
def put_baskets(request: Request, body: BasketsRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    payload = TradeBaskets.model_validate(body.model_dump(exclude={"expected_version", "request_id"})).model_dump(mode="json")
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
