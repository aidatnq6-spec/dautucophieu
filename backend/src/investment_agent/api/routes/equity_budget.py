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


class Layers(ContractModel):
    deposit: str = Field(max_length=24)
    bond: str = Field(max_length=24)
    gold: str = Field(max_length=24)
    crypto: str = Field(max_length=24)


class BudgetRequest(ContractModel):
    total: str | None = Field(default=None, max_length=24)  # one figure, or…
    layers: Layers | None = None                           # …Tháp tài sản: the total becomes the sum of the layers
    reserve: str | None = Field(default=None, max_length=24)  # None = use the profile's emergency reserve and 12-month needs
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
    def whole(raw):
        try:
            value = Decimal(raw)
        except InvalidOperation:
            return None
        return value if value.is_finite() and value >= 0 and value == value.to_integral_value() else None
    if body.layers is None and body.total is None:
        return error(422, "invalid_total", "Cần tổng tài sản hoặc số tiền từng lớp.")
    layers = None
    if body.layers is not None:
        layers = {k: whole(v) for k, v in body.layers.model_dump().items()}
        if any(v is None for v in layers.values()):
            return error(422, "invalid_layers", "Số tiền từng lớp phải là số đồng không âm.")
    total = whole(body.total) if body.total is not None else sum(layers.values(), Decimal(0))
    if total is None:
        return error(422, "invalid_total", "Tổng tài sản phải là số đồng không âm.")
    reserve = None
    if body.reserve is not None:
        try:
            reserve = Decimal(body.reserve)
        except InvalidOperation:
            return error(422, "invalid_reserve", "Quỹ dự phòng không hợp lệ.")
        if not reserve.is_finite() or reserve < 0 or reserve != reserve.to_integral_value():
            return error(422, "invalid_reserve", "Quỹ dự phòng phải là số đồng không âm.")
    payload = {"total": format(total, "f"), "reserve": format(reserve, "f") if reserve is not None else None,
               "layers": {k: format(v, "f") for k, v in layers.items()} if layers else None}
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        budget, version = budget_view(repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return {"version": version, "budget": budget}
