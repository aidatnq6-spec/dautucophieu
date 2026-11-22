"""Việc cuối năm on Năm tài chính (owner, 22/11/2026; docs/superpowers/specs/2026-11-22-nam-tai-chinh-design.md)."""

from datetime import timezone
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services import year_end

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class TickRequest(ContractModel):
    item: Literal["dividends", "cashflow"]
    done: bool = Field(strict=True)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _facts(request: Request, repo, owner, today) -> dict:
    from investment_agent.domain.pinned import CONFIG_DIR
    from investment_agent.services.deposit_book import book_quotes
    data_dir = request.app.state.data_dir
    quotes = book_quotes(Path(data_dir)) if data_dir is not None else {}
    return year_end.gather_facts(repo, owner, data_dir=Path(data_dir) if data_dir is not None else None, config_dir=CONFIG_DIR,
                                 today=today, now=now(request).astimezone(timezone.utc), quotes=quotes)


@router.get("/year-end")
def get_year_end(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    today = now(request).astimezone(VN).date()
    try:
        facts = _facts(request, repo, owner, today) if year_end.checklist_year(today) else {}
        return year_end.view(repo, owner, today=today, facts=facts)
    except RepositoryUnavailable:
        return unavailable()


@router.post("/year-end/tick")
def post_year_end_tick(request: Request, body: TickRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    today = now(request).astimezone(VN).date()
    try:
        return year_end.tick(repo, owner, today=today, item=body.item, done=body.done, expected_version=body.expected_version,
                             request_id=body.request_id, facts=_facts(request, repo, owner, today))
    except year_end.YearEndError as exc:
        return error(422, "year_end_closed", str(exc))
    except WRITE_ERRORS as exc:
        return write_error(exc)


@router.get("/year-review/{year}")
def get_year_review(request: Request, year: int):
    """Tổng kết năm of one year, from 2020 to the current year."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    today = now(request).astimezone(VN).date()
    if not 2020 <= year <= today.year:
        return error(422, "invalid_year", f"Chọn một năm từ 2020 đến {today.year}.")
    from investment_agent.services.deposit_book import book_quotes
    data_dir = request.app.state.data_dir
    try:
        return year_end.year_review(repo, owner, data_dir=Path(data_dir) if data_dir is not None else None, year=year, today=today,
                                    quotes=book_quotes(Path(data_dir)) if data_dir is not None else {})
    except RepositoryUnavailable:
        return unavailable()


class GoalsRequest(ContractModel):
    contribution: str | None = Field(default=None, max_length=24)
    savings_rate: str | None = Field(default=None, max_length=12)
    total_assets: str | None = Field(default=None, max_length=24)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _goal_args(request: Request) -> dict:
    from investment_agent.services.deposit_book import book_quotes
    data_dir = request.app.state.data_dir
    return {"data_dir": Path(data_dir) if data_dir is not None else None, "quotes": book_quotes(Path(data_dir)) if data_dir is not None else {}}


@router.get("/year-goals/{year}")
def get_year_goals(request: Request, year: int):
    """Mục tiêu năm: this year's or next year's goals and where they stand."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    today = now(request).astimezone(VN).date()
    if year not in (today.year, today.year + 1):
        return error(422, "invalid_year", f"Mục tiêu đặt cho năm {today.year} hoặc {today.year + 1}.")
    try:
        return year_end.goals_view(repo, owner, year=year, today=today, **_goal_args(request))
    except RepositoryUnavailable:
        return unavailable()


@router.put("/year-goals/{year}")
def put_year_goals(request: Request, year: int, body: GoalsRequest):
    from investment_agent.domain.year_goals import GoalError
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    today = now(request).astimezone(VN).date()
    if year not in (today.year, today.year + 1):
        return error(422, "invalid_year", f"Mục tiêu đặt cho năm {today.year} hoặc {today.year + 1}.")
    try:
        raw = {"contribution": body.contribution, "savings_rate": body.savings_rate, "total_assets": body.total_assets}
        return year_end.save_goals(repo, owner, year=year, raw=raw, expected_version=body.expected_version, request_id=body.request_id,
                                   today=today, **_goal_args(request))
    except GoalError as exc:
        return error(422, "invalid_goals", str(exc))
    except WRITE_ERRORS as exc:
        return write_error(exc)
