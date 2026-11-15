"""Kho tiền on Ngành theo quý: the watched non-financial tickers by net cash against their market value. Nothing personal is read."""

from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.services.cash_rank import CASH_RICH, cash_ranking

from ..auth import require_owner
from .common import unavailable

router = APIRouter(prefix="/internal/market")


@router.get("/cash-ranking")
def cash_rank(request: Request):
    require_owner(request)
    if request.app.state.data_dir is None:
        return unavailable()
    return {"rows": cash_ranking(Path(request.app.state.data_dir)), "cash_rich_from": format(CASH_RICH, "f")}
