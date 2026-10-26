"""Owner settings: the trading fee rate, and the reference-valuation parameters (required return, growth, threshold)."""

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import (PortfolioSettings, TradingSettings, ValuationSettings, portfolio_settings,  # noqa: F401
                                               trading_settings, valuation_settings)

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


class PortfolioRequest(ContractModel):
    settings: PortfolioSettings
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


@router.get("/portfolio")
def get_portfolio(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        settings, version = portfolio_settings(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    return {"version": version, "settings": settings.model_dump(mode="json")}


@router.put("/portfolio")
def put_portfolio(request: Request, body: PortfolioRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record = repo.write(owner, "settings", "portfolio", body.settings.model_dump(mode="json"), expected_version=body.expected_version,
                            request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return {"version": record.version, "settings": record.payload}


@router.get("/ai")
def ai_status(request: Request):
    """Read-only AI status for the Cài đặt page: key presence (last 4 characters only), approved policy, this month's spend."""
    from datetime import datetime, timezone
    from decimal import ROUND_HALF_UP, Decimal
    from pathlib import Path

    from investment_agent.ai.budget import SpendLedger
    from investment_agent.ai.openrouter import load_ai_policy
    from investment_agent.domain.pinned import CONFIG_DIR
    from investment_agent.settings import Settings

    require_owner(request)
    keys = Settings.from_env()
    approved = CONFIG_DIR / "ai-policy.json"
    policy = load_ai_policy(approved if approved.is_file() else CONFIG_DIR / "ai-policy.example.json")
    task = policy.tasks.get("insights")
    month = datetime.fromtimestamp(request.app.state.clock(), timezone.utc).strftime("%Y-%m")
    used, calls = Decimal(0), 0
    data_dir = request.app.state.data_dir
    ledger_path = Path(data_dir) / "ai" / "spend.sqlite" if data_dir is not None else None
    if ledger_path is not None and ledger_path.is_file():  # never create the ledger just to show the status
        rows = [r for r in SpendLedger(ledger_path)._rows("month = ?", (month,)) if r[0] != "released"]
        used, calls = SpendLedger._counted(rows), len(rows)
    return {"key": {"configured": bool(keys.openrouter_api_key), "hint": keys.key_hint()},
            "policy": {"version": policy.version, "status": policy.status, "monthly_usd": str(policy.budget.monthly_usd),
                       "models": list(task.models) if task else []},
            "spend": {"month": month, "used_usd": str(used.quantize(Decimal("0.0001"), ROUND_HALF_UP)), "calls": calls}}
