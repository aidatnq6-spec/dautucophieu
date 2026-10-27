"""Mục tiêu dòng tiền thụ động on Hồ sơ & rủi ro: the goal (`settings/passive_income`), the capital from Tháp tài sản, the monthly
contribution from Góp vốn đều, and an assumed yearly rate (the 12-month deposit rate unless the owner sets one)."""

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.ledger import replay
from investment_agent.domain.passive_income import income_by_layer, passive_income
from investment_agent.market.corporate_events import EventStore
from investment_agent.market.leading import MacroStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.contributions import PLAN as CONTRIBUTION_PLAN
from investment_agent.services.equity_budget import budget_view
from investment_agent.services.records import LedgerBook, read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal")
RECORD = ("settings", "passive_income")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
BOND_RATE = "7"  # the owner's bonds pay 7%/năm (owner, 27/10/2026); editable with the goal


class GoalRequest(ContractModel):
    target: str = Field(max_length=24)
    rate: str | None = Field(default=None, max_length=8)  # percent per year; None = the 12-month deposit rate
    bond_rate: str | None = Field(default=None, max_length=8)  # coupon of the bonds held, percent per year; None = 7
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def dividends_last_year(data_dir, repo, owner, today) -> Decimal:
    """Cash dividends per share with an ex-date in the last 12 months, times the shares held now (an estimate of what they paid)."""
    if data_dir is None:
        return Decimal(0)
    state = replay(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events))
    shares = {p.security_id: p.quantity + p.pending_quantity for p in state.positions if p.quantity + p.pending_quantity > 0}
    since = (today - timedelta(days=365)).isoformat()
    total = Decimal(0)
    for e in EventStore(Path(data_dir)).events(sorted(shares)):
        if e.get("kind") == "dividend_cash" and e.get("value_per_share") and e.get("exright") and since <= e["exright"] <= today.isoformat():
            total += Decimal(str(e["value_per_share"])) * shares[e["symbol"]]
    return total


def _view(request: Request, repo, owner) -> dict:
    data_dir = request.app.state.data_dir
    deposits = MacroStore(Path(data_dir)).read("deposit_12m") if data_dir is not None else []
    default_rate = deposits[-1]["value"] if deposits else None
    record = read_version(repo, owner, *RECORD, None)
    budget, _ = budget_view(repo, owner)
    capital = Decimal(budget["base"]) if budget.get("status") == "ok" else None
    plan = read_version(repo, owner, *CONTRIBUTION_PLAN, None)
    contribution = Decimal(plan.payload["amount"]) if plan else Decimal(0)
    today = now(request).astimezone(VN).date()
    income = None
    pyramid = budget.get("pyramid") if budget.get("status") == "ok" else None
    if pyramid and default_rate is not None:
        layers = {l["id"]: Decimal(l["amount"]) for l in pyramid["layers"]}
        bond_rate = (record.payload.get("bond_rate") if record else None) or BOND_RATE
        income = income_by_layer(deposit=layers.get("deposit", Decimal(0)), deposit_rate=Decimal(default_rate), bond=layers.get("bond", Decimal(0)),
                                 bond_rate=Decimal(bond_rate), dividends_12m=dividends_last_year(data_dir, repo, owner, today))
    result = None
    if record is not None:
        rate = record.payload.get("rate") or default_rate
        if rate is not None:
            result = {**passive_income(target=Decimal(record.payload["target"]), rate=Decimal(rate), capital=capital, contribution=contribution,
                                       today=today, income_now=Decimal(income["total"]) if income else None), "rate": rate}
    goal = {**record.payload, "bond_rate": record.payload.get("bond_rate") or BOND_RATE} if record else None
    return {"version": record.version if record else 0, "goal": goal, "default_rate": default_rate, "default_bond_rate": BOND_RATE,
            "income": income, "result": result, "capital": format(capital, "f") if capital is not None else None, "contribution": format(contribution, "f")}


@router.get("/passive-income")
def get_passive_income(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/passive-income")
def put_passive_income(request: Request, body: GoalRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        target = Decimal(body.target)
        rate = Decimal(body.rate) if body.rate is not None else None
        bond_rate = Decimal(body.bond_rate) if body.bond_rate is not None else None
    except InvalidOperation:
        return error(422, "invalid_goal", "Mục tiêu và tỷ suất phải là số.")
    if not target.is_finite() or target <= 0 or target != target.to_integral_value():
        return error(422, "invalid_goal", "Dòng tiền mong muốn phải là số đồng lớn hơn 0.")
    if rate is not None and not (rate.is_finite() and Decimal("0.1") <= rate <= Decimal(30)):
        return error(422, "invalid_rate", "Tỷ suất giả định từ 0,1% đến 30%/năm.")
    if bond_rate is not None and not (bond_rate.is_finite() and Decimal(0) <= bond_rate <= Decimal(30)):
        return error(422, "invalid_rate", "Lãi suất trái phiếu từ 0% đến 30%/năm.")
    payload = {"target": format(target, "f"), "rate": format(rate, "f") if rate is not None else None,
               "bond_rate": format(bond_rate, "f") if bond_rate is not None else None}
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
