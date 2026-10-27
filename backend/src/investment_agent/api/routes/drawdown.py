"""Kế hoạch sụt giảm on the Danh mục page: deepest falls over the full stored history, the fall now, and price against cost."""

from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.drawdown import INDICES, drawdown_rows, held_costs, last_close, watch_rows, watched
from investment_agent.services.records import portfolio_settings

from ..auth import require_owner
from .common import unavailable

router = APIRouter(prefix="/internal")


@router.get("/drawdown")
def get_drawdown(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir = request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    try:
        costs = held_costs(repo, owner)
        settings, _ = portfolio_settings(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    series, market = SeriesStore(Path(data_dir) / "trend-sources"), request.app.state.market
    prices = {i: last_close(series, i) for i in INDICES}
    for symbol in costs:
        point = market.price(symbol)
        prices[symbol] = format(point.price, "f") if point is not None else last_close(series, symbol)
    return {"threshold": str(settings.drawdown_threshold), "rows": drawdown_rows(data_dir, costs, prices, settings.drawdown_threshold),
            "watch": watch_rows(data_dir, watched(data_dir, costs))}
