"""Sức khỏe tài chính on Hồ sơ & rủi ro: monthly income, expenses and birth year (personal; `settings/wealth_check`), checked against
the rule that the savings rate should be at least one's age in percent."""

from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.wealth_check import wealth_check
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal")
RECORD = ("settings", "wealth_check")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class WealthRequest(ContractModel):
    income: str = Field(max_length=24)
    expenses: str = Field(max_length=24)
    birth_year: int = Field(strict=True)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, record) -> dict:
    if record is None:
        return {"version": 0, "inputs": None, "check": None}
    p = record.payload
    check = wealth_check(income=Decimal(p["income"]), expenses=Decimal(p["expenses"]), birth_year=p["birth_year"],
                         today=now(request).astimezone(VN).date())
    return {"version": record.version, "inputs": p, "check": check}


@router.get("/wealth-check")
def get_wealth_check(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, read_version(repo, owner, *RECORD, None))
    except RepositoryUnavailable:
        return unavailable()


@router.put("/wealth-check")
def put_wealth_check(request: Request, body: WealthRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        income, expenses = Decimal(body.income), Decimal(body.expenses)
    except InvalidOperation:
        return error(422, "invalid_amount", "Thu nhập và chi tiêu phải là số đồng.")
    whole = lambda v: v.is_finite() and v == v.to_integral_value()  # noqa: E731
    if not (whole(income) and whole(expenses)) or income <= 0 or expenses < 0:
        return error(422, "invalid_amount", "Thu nhập phải lớn hơn 0 và chi tiêu không âm (số đồng).")
    this_year = now(request).astimezone(VN).year
    if not this_year - 100 <= body.birth_year <= this_year - 15:
        return error(422, "invalid_birth_year", "Năm sinh không hợp lệ.")
    payload = {"income": format(income, "f"), "expenses": format(expenses, "f"), "birth_year": body.birth_year}
    try:
        record = repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return _view(request, record)
