"""Bản tin tuần on the web (owner, 21/11/2026): the notes that went out over Telegram, kept one a week by services.weekly_brief."""

from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.services.weekly_brief import read_weekly, weekly_list

from ..auth import require_owner
from .common import error, unavailable

router = APIRouter(prefix="/internal/weekly-briefs")


@router.get("")
def weekly_briefs(request: Request):
    require_owner(request)
    if request.app.state.data_dir is None:
        return unavailable()
    weeks = weekly_list(Path(request.app.state.data_dir))
    return {"weeks": weeks, "latest": read_weekly(Path(request.app.state.data_dir), weeks[0]["week"]) if weeks else None}


@router.get("/{week}")
def weekly_brief(request: Request, week: str):
    require_owner(request)
    if request.app.state.data_dir is None:
        return unavailable()
    found = read_weekly(Path(request.app.state.data_dir), week)
    return found if found else error(404, "weekly_missing", "Không có bản tin tuần này.")
