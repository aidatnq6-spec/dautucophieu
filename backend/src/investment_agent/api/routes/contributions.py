"""Góp vốn đều on Hồ sơ & rủi ro: the monthly plan and the months, streak and totals read from the ledger."""

import re
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.contributions import contribution_status
from investment_agent.domain.models import ContractModel
from investment_agent.domain.wealth_check import wealth_check
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.contributions import PLAN, cash_flows
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class PlanRequest(ContractModel):
    amount: str = Field(max_length=24)
    day: int = Field(strict=True)
    start: str = Field(max_length=7)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    today = now(request).astimezone(VN).date()
    record = read_version(repo, owner, *PLAN, None)
    suggested = None
    wc = read_version(repo, owner, "settings", "wealth_check", None)
    if wc is not None:
        p = wc.payload
        savings = Decimal(wealth_check(income=Decimal(p["income"]), expenses=Decimal(p["expenses"]), birth_year=p["birth_year"], today=today)["savings"])
        suggested = format(savings, "f") if savings > 0 else None
    status = contribution_status(cash_flows(repo, owner), record.payload, today=today) if record else None
    return {"version": record.version if record else 0, "plan": record.payload if record else None, "status": status, "suggested_amount": suggested}


@router.get("/contributions")
def get_contributions(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/contributions")
def put_contributions(request: Request, body: PlanRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        amount = Decimal(body.amount)
    except InvalidOperation:
        return error(422, "invalid_amount", "Số tiền góp phải là số đồng.")
    if not amount.is_finite() or amount <= 0 or amount != amount.to_integral_value():
        return error(422, "invalid_amount", "Số tiền góp phải là số đồng lớn hơn 0.")
    if not 1 <= body.day <= 28:
        return error(422, "invalid_day", "Ngày góp từ 1 đến 28.")
    if not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", body.start):
        return error(422, "invalid_start", "Tháng bắt đầu không hợp lệ.")
    try:
        repo.write(owner, *PLAN, {"amount": format(amount, "f"), "day": body.day, "start": body.start}, expected_version=body.expected_version,
                   request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
