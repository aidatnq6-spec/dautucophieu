"""Kho tiền on Ngành theo quý: the watched non-financial tickers by net cash against their market value. Nothing personal is read."""

from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.services.cash_rank import CASH_RICH, cash_ranking
from investment_agent.services.receivable_signs import SIGNS, receivable_signs

from ..auth import require_owner
from .common import unavailable

router = APIRouter(prefix="/internal/market")


@router.get("/cash-ranking")
def cash_rank(request: Request):
    require_owner(request)
    if request.app.state.data_dir is None:
        return unavailable()
    return {"rows": cash_ranking(Path(request.app.state.data_dir)), "cash_rich_from": format(CASH_RICH, "f")}


@router.get("/receivable-signs")
def receivable_board(request: Request):
    """Bảng dấu hiệu phải thu: which receivable signs each watched non-financial ticker has on, most first."""
    require_owner(request)
    if request.app.state.data_dir is None:
        return unavailable()
    return {"signs": [{"key": k, "title": t} for k, t in SIGNS], "rows": receivable_signs(Path(request.app.state.data_dir))}
