"""Mùa báo cáo: the season view of the watched tickers, and the review the owner records after a held ticker reports."""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.earnings_season import REVIEWS, read_reviews, season_view

from ..auth import require_owner
from .common import WRITE_ERRORS, now, unavailable, write_error

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class ReviewRequest(ContractModel):
    symbol: str = Field(pattern=r"^[A-Z0-9]{3,10}$")
    quarter: str = Field(pattern=r"^\d{4}-Q[1-4]$")
    verdict: Literal["keep", "watch", "revisit"]
    note: str = Field(default="", max_length=500)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    return season_view(request.app.state.data_dir, repo, owner, today=now(request).astimezone(VN).date())


@router.get("/earnings")
def get_earnings(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/earnings/reviews")
def put_review(request: Request, body: ReviewRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    try:
        reviews, _ = read_reviews(repo, owner)
        entry = {"symbol": body.symbol, "quarter": body.quarter, "verdict": body.verdict, "note": body.note.strip(),
                 "at": now(request).astimezone(VN).isoformat(timespec="seconds")}
        kept = [r for r in reviews if (r["symbol"], r["quarter"]) != (body.symbol, body.quarter)]
        repo.write(owner, *REVIEWS, {"reviews": [*kept, entry][-2000:]}, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
