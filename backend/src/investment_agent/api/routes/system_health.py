"""Tình trạng hệ thống on Cài đặt: whether the unattended work is really happening."""

from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.services.system_health import health_report

from ..auth import require_owner
from .common import now, unavailable

router = APIRouter(prefix="/internal")


@router.get("/system-health")
def system_health(request: Request):
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    return health_report(Path(data_dir), now=now(request))
