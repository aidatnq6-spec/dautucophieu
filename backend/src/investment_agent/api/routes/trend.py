"""Latest Xu hướng board (MACD/RSI by frame) built by the after-close schedule, and the price board and candles beside it."""

from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel

from investment_agent.market.live_board import INDICES, ChartStore, build_board, chart, in_session
from investment_agent.market.macro_board import IDS as MACRO_IDS
from investment_agent.market.macro_board import macro_chart, macro_rows
from investment_agent.market.trend import SnapshotStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.price_alerts import AlertError, change_alerts, read_alerts
from investment_agent.services.records import notification_settings
from investment_agent.settings import Settings

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

# One board read serves every poll for a while: Vnstock's free tier allows 60 calls a minute.
BOARD_TTL = {True: timedelta(seconds=15), False: timedelta(minutes=5)}
MACRO_TTL = timedelta(seconds=15)
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
    """Indices and watched tickers (Vnstock) cached 15 s in the session, 5 min outside it; Vĩ mô rows (Coinbase live, stored closes)
    cached 15 s at any hour, since Bitcoin and gold trade around the clock."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    symbols = list(load_watchlist(Path(data_dir)).symbols)
    moment = now(request)
    source = _source()
    key = f"{data_dir}|{','.join(symbols)}"
    cached = _board_cache.get(key)
    if cached and moment - cached[0] < BOARD_TTL[in_session(moment)]:
        board = cached[1]
    else:
        board = build_board(symbols, board=source.board, index_minutes=source.index_minutes, now=moment)
        _board_cache[key] = (moment, board)
    macro = _board_cache.get(f"{data_dir}|macro")
    if not macro or moment - macro[0] >= MACRO_TTL:
        macro = (moment, macro_rows(Path(data_dir), get=source.get, now=moment))
        _board_cache[f"{data_dir}|macro"] = macro
    indices = [r for r in board["rows"] if r["kind"] == "index"]
    return {**board, "as_of": max(board["as_of"], macro[0].isoformat()), "stocks_as_of": board["as_of"],
            "rows": indices + macro[1] + board["rows"][len(indices):]}


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


class AlertChange(ContractModel):
    action: str = Field(pattern=r"^(add|remove|rearm)$")
    id: str | None = Field(default=None, max_length=32)
    symbol: str | None = Field(default=None, max_length=10)
    op: str | None = Field(default=None, max_length=8)
    price: str | None = Field(default=None, max_length=16)
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _alerts_view(request: Request, alerts: list[dict], version: int) -> dict:
    owner, repo = require_owner(request), request.app.state.personal_repository
    chosen, _ = notification_settings(repo, owner)
    ready = bool(Settings.from_env().telegram_bot_token and chosen.enabled and chosen.scheduled_enabled and chosen.chat_id)
    return {"version": version, "alerts": alerts, "telegram_ready": ready}


@router.get("/trend/alerts")
def price_alerts(request: Request):
    """Cảnh báo giá: the owner's levels and whether scheduled Telegram delivery is on (they are sent only then)."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _alerts_view(request, *read_alerts(repo, owner))
    except RepositoryUnavailable:
        return unavailable()


@router.put("/trend/alerts")
def price_alerts_change(request: Request, body: AlertChange):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir = request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    allowed = set(load_watchlist(Path(data_dir)).symbols) | set(INDICES)
    try:
        alerts, version = change_alerts(repo, owner, body.model_dump(exclude={"expected_version", "request_id"}), expected_version=body.expected_version,
                                        request_id=body.request_id, allowed=allowed, now=now(request))
        return _alerts_view(request, alerts, version)
    except AlertError as exc:
        return error(422, exc.code, exc.message)
    except WRITE_ERRORS as exc:
        return write_error(exc)
