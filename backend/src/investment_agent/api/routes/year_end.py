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
