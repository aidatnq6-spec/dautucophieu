"""Reference valuation of the watched tickers (Định giá page): computed on request from stored statements."""

from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import valuation_settings
from investment_agent.valuation.reference import Settings, reference_board, year_end_prices

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
        settings, _ = valuation_settings(repo, owner)
        held = held_tickers(request)
    except RepositoryUnavailable:
        return unavailable()
    data_dir, today, market = Path(data_dir), now(request).astimezone(VN).date(), request.app.state.market
    symbols = list(load_watchlist(data_dir).symbols)
    store, series = FundamentalsStore(data_dir / "fundamentals"), SeriesStore(data_dir / "trend-sources")
    records = {s: store.read(s) for s in symbols}
    prices = {s: p.price for s in symbols if (p := market.price(s)) is not None}
    board = reference_board(symbols, sectors=load_sectors(data_dir)[0], records=records, prices=prices,
                            year_end={s: year_end_prices(series.read(f"{s}-1d"), today=today) for s in symbols},
                            settings=Settings(settings.required_return, settings.long_term_growth, settings.threshold), today=today, held=held)
    for row in board["rows"]:
        for m in row["methods"]:
            m["value"] = str(m["value"]) if m["value"] is not None else None
    return board
