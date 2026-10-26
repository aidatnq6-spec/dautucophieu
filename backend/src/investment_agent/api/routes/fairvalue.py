"""Reference valuation of the watched tickers (Định giá page): computed on request from stored statements."""

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.holdings_view import fair_value_board

from ..auth import require_owner
from .common import now, unavailable
from .watchlist import held_tickers

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


@router.get("/fairvalue")
def fairvalue(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir = request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    try:
        board = fair_value_board(data_dir, request.app.state.market, repo, owner, held=held_tickers(request),
                                 today=now(request).astimezone(VN).date())
    except RepositoryUnavailable:
        return unavailable()
    for row in board["rows"]:
        for m in row["methods"]:
            m["value"] = str(m["value"]) if m["value"] is not None else None
    return board
