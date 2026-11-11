"""Dự án và điểm rơi lợi nhuận on a watched property developer's page: the owner's own reading of the company's public documents,
kept in a settings record per ticker."""

import re
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.property_projects import MAX_PROJECTS, ProjectError, timeline, validate_projects
from investment_agent.market.sectors import load_sectors
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, unavailable, write_error

router = APIRouter(prefix="/internal")
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
PROPERTY = "Bất động sản"


class ProjectsRequest(ContractModel):
    projects: list[dict] = Field(max_length=MAX_PROJECTS)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _developer(request: Request, symbol: str) -> str | None:
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return None
    symbol = symbol.upper()
    ok = _SYMBOL.fullmatch(symbol) and symbol in load_watchlist(Path(data_dir)).symbols and load_sectors(Path(data_dir))[0].get(symbol) == PROPERTY
    return symbol if ok else None


def _view(repo, owner, symbol: str) -> dict:
    record = read_version(repo, owner, "settings", f"property_projects_{symbol}", None)
    return {"symbol": symbol, "version": record.version if record else 0, **timeline((record.payload if record else {}).get("projects", []))}


@router.get("/stock/{symbol}/projects")
def get_projects(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    if not (sym := _developer(request, symbol)):
        return error(404, "not_a_developer", "Chỉ ghi dự án cho mã bất động sản trong danh sách theo dõi.")
    try:
        return _view(repo, owner, sym)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/stock/{symbol}/projects")
def put_projects(symbol: str, request: Request, body: ProjectsRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    if not (sym := _developer(request, symbol)):
        return error(404, "not_a_developer", "Chỉ ghi dự án cho mã bất động sản trong danh sách theo dõi.")
    try:
        projects = validate_projects(body.projects)
        repo.write(owner, "settings", f"property_projects_{sym}", {"symbol": sym, "projects": projects}, expected_version=body.expected_version,
                   request_id=body.request_id)
        return _view(repo, owner, sym)
    except ProjectError as exc:
        return error(422, exc.code, exc.message)
    except WRITE_ERRORS as exc:
        return write_error(exc)
