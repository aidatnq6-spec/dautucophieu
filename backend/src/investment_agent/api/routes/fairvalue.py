"""Reference valuation of the watched tickers (Định giá page): computed on request from stored statements."""

from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.index_valuation import INDICES, series_key
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.holdings_view import fair_value_board
from investment_agent.valuation.history import monthly_multiples
from investment_agent.valuation.index_reference import index_monthly_multiples

from ..auth import require_owner
from .common import error, now, unavailable
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


@router.get("/fairvalue/history/{symbol}")
def fairvalue_history(symbol: str, request: Request):
    """Monthly P/E and P/B of one watched ticker or of VNINDEX/VN30 (public statements, prices and index multiples only)."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    data_dir, symbol = Path(data_dir), symbol.upper()
    if symbol in INDICES:
        multiples = SeriesStore(data_dir / "index-valuation")
        return index_monthly_multiples(symbol, pe=multiples.read(series_key(symbol, "pe")), pb=multiples.read(series_key(symbol, "pb")))
    if symbol not in load_watchlist(data_dir).symbols:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    out = monthly_multiples(FundamentalsStore(data_dir / "fundamentals").read(symbol), SeriesStore(data_dir / "trend-sources").read(f"{symbol}-1d"),
                            today=now(request).astimezone(VN).date())
    return {"symbol": symbol, **out}
