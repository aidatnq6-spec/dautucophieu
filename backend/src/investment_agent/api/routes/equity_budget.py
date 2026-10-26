"""Vốn dành cho cổ phiếu on the Hồ sơ & rủi ro page: one total entered by the owner, computed against their risk group."""

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.equity_budget import RECORD, budget_view

from ..auth import require_owner
from .common import WRITE_ERRORS, error, unavailable, write_error

router = APIRouter(prefix="/internal")


class BudgetRequest(ContractModel):
    total: str = Field(max_length=24)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


@router.get("/equity-budget")
def get_budget(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        budget, version = budget_view(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    return {"version": version, "budget": budget}


@router.put("/equity-budget")
def put_budget(request: Request, body: BudgetRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        total = Decimal(body.total)
    except InvalidOperation:
        return error(422, "invalid_total", "Tổng tài sản không hợp lệ.")
    if not total.is_finite() or total < 0 or total != total.to_integral_value():
        return error(422, "invalid_total", "Tổng tài sản phải là số đồng không âm.")
    try:
        repo.write(owner, *RECORD, {"total": format(total, "f")}, expected_version=body.expected_version, request_id=body.request_id)
        budget, version = budget_view(repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return {"version": version, "budget": budget}
