"""Latest Xu hướng board (MACD/RSI by frame) built by the after-close schedule, and the price board and candles beside it."""

from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.market.live_board import INDICES, ChartStore, build_board, chart, in_session
from investment_agent.market.macro_board import IDS as MACRO_IDS
from investment_agent.market.macro_board import macro_chart, macro_rows
from investment_agent.market.trend import SnapshotStore
from investment_agent.market.watchlist import load_watchlist

from ..auth import require_owner
from .common import error, now, unavailable

# One board read serves every poll for a while: Vnstock's free tier allows 60 calls a minute.
BOARD_TTL = {True: timedelta(seconds=15), False: timedelta(minutes=5)}
_board_cache: dict[str, tuple] = {}

router = APIRouter(prefix="/internal")


@router.get("/trend")
def trend(request: Request):
    require_owner(request)
    if request.app.state.personal_repository is None:
        return unavailable()
    data_dir = request.app.state.data_dir
    return {"snapshot": SnapshotStore(Path(data_dir) / "trend").latest() if data_dir is not None else None}


class _Vnstock:
    """Vnstock's free tier behind the three reads the board and chart need, and a plain GET for Coinbase's public stats."""

    def __init__(self):
        from investment_agent.market.providers.vnstock_adapter import VnstockProvider
        self.provider = VnstockProvider()

    def board(self, symbols):
        from investment_agent.market.providers.vnstock_adapter import LIVE_FIELDS, price_board
        return price_board(symbols, LIVE_FIELDS)

    def index_minutes(self, index):
        from datetime import date
        today = date.today()
        return self.provider.index_minutes(index, today - timedelta(days=7), today)

    def get(self, url):
        import httpx
        response = httpx.get(url, timeout=10, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
        response.raise_for_status()
        return response.text

    def ohlcv(self, symbol, interval, start, end, index):
        return self.provider.ohlcv_rows(symbol, interval, start, end, index=index)


def _source():
    return _Vnstock()


@router.get("/trend/board")
def live_board(request: Request):
    """Indices, Vĩ mô rows and watched tickers (Vnstock, Coinbase, stored closes); cached 15 s in the session, 5 min outside it."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    symbols = list(load_watchlist(Path(data_dir)).symbols)
    moment = now(request)
    key = f"{data_dir}|{','.join(symbols)}"
    cached = _board_cache.get(key)
    if cached and moment - cached[0] < BOARD_TTL[in_session(moment)]:
        return cached[1]
    source = _source()
    payload = build_board(symbols, board=source.board, index_minutes=source.index_minutes, now=moment)
    indices = [r for r in payload["rows"] if r["kind"] == "index"]
    payload["rows"] = indices + macro_rows(Path(data_dir), get=source.get, now=moment) + payload["rows"][len(indices):]
    _board_cache[key] = (moment, payload)
    return payload


@router.get("/trend/chart/{symbol}/{interval}")
def live_chart(symbol: str, interval: str, request: Request):
    """Daily (10 years) or hourly (1 year) candles with MACD and RSI for an index or a watched ticker."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    if interval not in ("1D", "1H"):
        return error(422, "invalid_interval", "Khung chỉ có 1D hoặc 1H.")
    sym = symbol.upper()
    if sym in MACRO_IDS:
        return macro_chart(Path(data_dir), sym, interval)
    if sym not in INDICES and sym not in load_watchlist(Path(data_dir)).symbols:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    return chart(ChartStore(Path(data_dir)), sym, interval, fetch=_source().ohlcv, now=now(request), index=sym in INDICES)
