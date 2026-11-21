"""Sử dụng phần mềm on Cài đặt: page visits sent by the web app, and the summary with the slow requests (services.usage). Local only."""

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.services.usage import page_key, record_visit, usage_summary

from ..auth import require_owner
from .common import error, now

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class Visit(ContractModel):
    page: str = Field(max_length=200)


@router.post("/usage/visit")
def post_visit(request: Request, body: Visit):
    require_owner(request)
    page, data_dir = page_key(body.page), request.app.state.data_dir
    if page is None:
        return error(422, "invalid_page", "Trang không hợp lệ.")
    if data_dir is not None:
        record_visit(data_dir, page, today=now(request).astimezone(VN).date())
    return {"page": page}


@router.get("/usage")
def get_usage(request: Request):
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return {"pages": [], "slow": [], "slow_threshold": None, "since": None}
    return usage_summary(data_dir, today=now(request).astimezone(VN).date())
