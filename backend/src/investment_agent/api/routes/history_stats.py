"""Thống kê lịch sử: VN-Index some sessions later by P/E group and by the macro lights' levels (services.history_stats). Public data only."""

from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.services.history_stats import HORIZONS, history_stats

from ..auth import require_owner
from .common import error, now, unavailable

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


@router.get("/history-stats/states/{h}/{a}/{b}/{fx}")
def get_history_states(request: Request, h: int, a: str, b: str, fx: str):
    """The 2×2 of conditions a and b, VN-Index h sessions later; fx: the USD/VND condition's threshold in % over three months."""
    from investment_agent.domain.history_states import CONDITIONS
    from investment_agent.services.history_stats import FX_THRESHOLDS, history_states
    require_owner(request)
    if h not in HORIZONS or a not in CONDITIONS or b not in CONDITIONS or a == b or fx not in FX_THRESHOLDS:
        return error(422, "invalid_states", "Chọn số phiên 20, 60, 120 hoặc 250, hai điều kiện khác nhau và ngưỡng tỷ giá 0,5, 1, 2 hoặc 3%.")
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    return history_states(Path(data_dir), a=a, b=b, h=h, fx=fx, today=now(request).astimezone(VN).date())


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
