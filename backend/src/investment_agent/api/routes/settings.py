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


@router.get("/sources")
def sources(request: Request):
    """Tình trạng nguồn số liệu for Cài đặt: the last macro run and the public sources failing since, with how many runs in a row."""
    from pathlib import Path

    from investment_agent.services.source_alerts import THRESHOLD, macro_labels, source_view
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return {"last_run": None, "checked": 0, "failing": [], "threshold": THRESHOLD}
    return {**source_view(Path(data_dir), labels=macro_labels()), "threshold": THRESHOLD}


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


# Lợi nhuận tòa nhà: the owner's saved building plans, each the boxes as typed (strings), so the page can reopen and compare them.
class BuildingRow(ContractModel):
    name: str = Field(default="", max_length=60)
    count: str = Field(default="", max_length=20)
    price: str = Field(default="", max_length=30)
    life: str = Field(default="", max_length=10)


class BuildingPlanItem(ContractModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    name: str = Field(min_length=1, max_length=60, pattern=r"\S")
    saved_on: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    method: str = Field(pattern=r"^(annuity|declining)$")
    form: dict[str, str] = Field(max_length=60)
    rows: list[BuildingRow] = Field(default_factory=list, max_length=30)

    def model_post_init(self, __context) -> None:
        import re
        for key, value in self.form.items():
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,39}", key) or len(value) > 30:
                raise ValueError("bad form box")


class BuildingPlansRequest(ContractModel):
    plans: list[BuildingPlanItem] = Field(max_length=20)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


@router.get("/building-plans")
def get_building_plans(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record = read_version(repo, owner, "settings", "building_plans", None)
    except RepositoryUnavailable:
        return unavailable()
    return {"version": record.version if record else 0, "plans": (record.payload.get("plans") if record else None) or []}


@router.put("/building-plans")
def put_building_plans(request: Request, body: BuildingPlansRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record = repo.write(owner, "settings", "building_plans", {"plans": [p.model_dump(mode="json") for p in body.plans]},
                            expected_version=body.expected_version, request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return {"version": record.version, "plans": record.payload["plans"]}
