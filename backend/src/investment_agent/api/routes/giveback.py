"""Lãi đã trả lại thị trường and Mục tiêu đã đủ tiền on the Danh mục page. Personal data; never sent to a model."""

from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.giveback import SpendGoals, giveback_for, write_goals
from investment_agent.services.weekly_brief import VN

from ..auth import require_owner
from .common import WRITE_ERRORS, now, unavailable, write_error

router = APIRouter(prefix="/internal")


class GoalsRequest(SpendGoals):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


@router.get("/giveback")
def get_giveback(request: Request):
    owner, repo, data_dir = require_owner(request), request.app.state.personal_repository, request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    try:
        return giveback_for(repo, owner, Path(data_dir), today=now(request).astimezone(VN).date())
    except RepositoryUnavailable:
        return unavailable()


@router.put("/spend-goals")
def put_goals(request: Request, body: GoalsRequest):
    owner, repo, data_dir = require_owner(request), request.app.state.personal_repository, request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    goals = body.model_dump(mode="json", exclude={"expected_version", "request_id"})["goals"]
    try:
        write_goals(repo, owner, goals, expected_version=body.expected_version, request_id=body.request_id)
        return giveback_for(repo, owner, Path(data_dir), today=now(request).astimezone(VN).date())
    except WRITE_ERRORS as exc:
        return write_error(exc)
