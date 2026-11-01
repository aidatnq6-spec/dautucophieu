"""Bộ lọc tín hiệu on Theo dõi: every watched ticker's signal values from stored data, the criteria, and the owner's saved screens."""

from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.screener import CRITERIA, ScreenError
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.screener import change_screens, gather_rows, read_screens, signal_dates
from investment_agent.services.weekly_brief import VN

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error
from .watchlist import held_tickers

router = APIRouter(prefix="/internal")


def _view(request: Request, screens: list[dict], version: int) -> dict:
    owner, repo, data_dir = require_owner(request), request.app.state.personal_repository, request.app.state.data_dir
    rows = gather_rows(Path(data_dir), repo, owner, held=held_tickers(request), today=now(request).astimezone(VN).date(),
                       market=request.app.state.market) if data_dir is not None else []
    return {"version": version, "screens": screens, "rows": rows,
            "as_of": signal_dates(Path(data_dir)) if data_dir is not None else {"trend": None, "foreign": None},
            "criteria": {k: {"label": label, "values": values} for k, (label, values) in CRITERIA.items()}}


@router.get("/screener")
def screener(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, *read_screens(repo, owner))
    except RepositoryUnavailable:
        return unavailable()


class ScreenChange(ContractModel):
    action: str = Field(pattern=r"^(save|delete)$")
    id: str | None = Field(default=None, max_length=32)
    screen: dict | None = None
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


@router.put("/screener")
def screener_change(request: Request, body: ScreenChange):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        screens, version = change_screens(repo, owner, body.model_dump(exclude={"expected_version", "request_id"}),
                                          expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, screens, version)
    except ScreenError as exc:
        return error(422, exc.code, exc.message)
    except WRITE_ERRORS as exc:
        return write_error(exc)
