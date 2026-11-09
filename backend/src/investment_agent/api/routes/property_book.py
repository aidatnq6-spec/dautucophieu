"""Bất động sản và khoản vay on Hồ sơ & rủi ro, with the whole picture of what the owner has and owes."""

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.property_book import PropertyBook
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.property_book import RECORD, property_view

from ..auth import require_owner
from .common import WRITE_ERRORS, now, unavailable, write_error

router = APIRouter(prefix="/internal")


class BookRequest(PropertyBook):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    return property_view(repo, owner, market=request.app.state.market, data_dir=request.app.state.data_dir, now=now(request))


@router.get("/property-book")
def get_book(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/property-book")
def put_book(request: Request, body: BookRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    payload = PropertyBook.model_validate(body.model_dump(exclude={"expected_version", "request_id"})).model_dump(mode="json")
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
