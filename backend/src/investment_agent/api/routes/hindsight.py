"""Hậu kiểm quyết định on Nhật ký: how past buys, sells and holds turned out."""

from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.hindsight import hindsight_for
from investment_agent.services.weekly_brief import VN

from ..auth import require_owner
from .common import now, unavailable

router = APIRouter(prefix="/internal")


@router.get("/hindsight")
def get_hindsight(request: Request):
    owner, repo, data_dir = require_owner(request), request.app.state.personal_repository, request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    try:
        return hindsight_for(repo, owner, Path(data_dir), today=now(request).astimezone(VN).date())
    except RepositoryUnavailable:
        return unavailable()
