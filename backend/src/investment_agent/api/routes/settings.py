"""Owner trading settings: the fee rate used to keep buy proposals within buying power."""

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel, Ratio
from investment_agent.repositories.personal import RepositoryUnavailable

from ..auth import require_owner
from .common import WRITE_ERRORS, read_version, unavailable, write_error

router = APIRouter(prefix="/internal/settings")


class TradingSettings(ContractModel):
    fee_rate: Ratio  # owner's broker fee as a fraction of order value, from their fee schedule


class TradingRequest(ContractModel):
    settings: TradingSettings
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def trading_settings(repo, owner) -> TradingSettings | None:
    record = read_version(repo, owner, "settings", "trading", None)
    return TradingSettings.model_validate(record.payload) if record else None


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
