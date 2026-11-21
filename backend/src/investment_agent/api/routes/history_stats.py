"""Thống kê lịch sử: VN-Index some sessions later by P/E group and by the macro lights' levels (services.history_stats). Public data only."""

from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.services.history_stats import HORIZONS, history_stats

from ..auth import require_owner
from .common import error, now, unavailable

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


@router.get("/history-stats/{h}")
def get_history_stats(request: Request, h: int):
    """h: sessions ahead, as a path segment (the web proxy forwards no query string)."""
    require_owner(request)
    if h not in HORIZONS:
        return error(422, "invalid_horizon", "Số phiên phải là 20, 60, 120 hoặc 250.")
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    return history_stats(Path(data_dir), h=h, today=now(request).astimezone(VN).date())
