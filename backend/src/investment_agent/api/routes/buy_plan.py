"""Kế hoạch giải ngân on Danh mục & Giao dịch: the owner's tranches with how far each condition is."""

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.buy_plan import PlanError, plan_rows
from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.buy_plan import RECORD, merge, public_inputs, read_plan

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class PlanRequest(ContractModel):
    tranches: list[dict] = Field(max_length=40)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, tranches: list[dict], version: int) -> dict:
    closes, _ = public_inputs(request.app.state.data_dir, {t["symbol"] for t in tranches})
    return {"version": version, "tranches": plan_rows(tranches, closes=closes, today=now(request).astimezone(VN).date())}


@router.get("/buy-plan")
def get_plan(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, *read_plan(repo, owner))
    except RepositoryUnavailable:
        return unavailable()


@router.put("/buy-plan")
def put_plan(request: Request, body: PlanRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        tranches = merge(read_plan(repo, owner)[0], body.tranches)
        version = repo.write(owner, *RECORD, {"tranches": tranches}, expected_version=body.expected_version, request_id=body.request_id).version
        return _view(request, tranches, version)
    except PlanError as exc:
        return error(422, exc.code, exc.message)
    except WRITE_ERRORS as exc:
        return write_error(exc)
