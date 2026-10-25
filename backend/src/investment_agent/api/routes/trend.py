"""Latest Xu hướng board (MACD/RSI by frame) built by the after-close schedule."""

from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.market.trend import SnapshotStore

from ..auth import require_owner
from .common import unavailable

router = APIRouter(prefix="/internal")


@router.get("/trend")
def trend(request: Request):
    require_owner(request)
    if request.app.state.personal_repository is None:
        return unavailable()
    data_dir = request.app.state.data_dir
    return {"snapshot": SnapshotStore(Path(data_dir) / "trend").latest() if data_dir is not None else None}
