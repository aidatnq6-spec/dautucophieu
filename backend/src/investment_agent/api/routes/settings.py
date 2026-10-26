"""Owner settings: the trading fee rate, and the reference-valuation parameters (required return, growth, threshold)."""

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import TradingSettings, ValuationSettings, trading_settings, valuation_settings  # noqa: F401

from ..auth import require_owner
from .common import WRITE_ERRORS, read_version, unavailable, write_error

router = APIRouter(prefix="/internal/settings")


class TradingRequest(ContractModel):
    settings: TradingSettings
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


@router.get("/trading")
def get_trading(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record = read_version(repo, owner, "settings", "trading", None)
    except RepositoryUnavailable:
        return unavailable()
    return {"version": record.version if record else 0, "settings": record.payload if record else None}


@router.put("/trading")
def put_trading(request: Request, body: TradingRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record = repo.write(owner, "settings", "trading", body.settings.model_dump(mode="json"), expected_version=body.expected_version,
                            request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return {"version": record.version, "settings": record.payload}


class ValuationRequest(ContractModel):
    settings: ValuationSettings
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


@router.get("/valuation")
def get_valuation(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        settings, version = valuation_settings(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    return {"version": version, "settings": settings.model_dump(mode="json")}


@router.put("/valuation")
def put_valuation(request: Request, body: ValuationRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record = repo.write(owner, "settings", "valuation", body.settings.model_dump(mode="json"), expected_version=body.expected_version,
                            request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return {"version": record.version, "settings": record.payload}
