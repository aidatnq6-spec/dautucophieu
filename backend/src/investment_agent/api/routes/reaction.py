"""Phản ứng giá sau báo cáo on a watched ticker's page: its stored statements' report days and profit, its adjusted closes and
VN-Index's. Public data only."""

import re
from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.domain.profit_bridge import profit_bridge
from investment_agent.domain.report_reaction import reaction
from investment_agent.market.financial_ratios import kind_of
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist

from ..auth import require_owner
from .common import error, unavailable

router = APIRouter(prefix="/internal")
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")


@router.get("/stock/{symbol}/reaction")
def report_reaction(symbol: str, request: Request):
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    symbol, data_dir = symbol.upper(), Path(data_dir)
    if not _SYMBOL.fullmatch(symbol) or symbol not in load_watchlist(data_dir).symbols:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    sector = load_sectors(data_dir)[0].get(symbol)
    record = StatementStore(data_dir / ("statements" if kind_of(sector) is None else "statements-financial")).read(symbol) or {}
    if not record.get("quarters"):
        return error(404, "no_statements", "Chưa có báo cáo tài chính của mã này.")
    series = SeriesStore(data_dir / "trend-sources")
    return {"symbol": symbol, **reaction(record["quarters"], record.get("quarters_created", {}), series.read(f"{symbol}-1d"), series.read("VNINDEX-1d"))}


_QUARTER = re.compile(r"^\d{4}-Q[1-4]$")


@router.get("/stock/{symbol}/profit-bridge")
@router.get("/stock/{symbol}/profit-bridge/{quarter}")
def get_profit_bridge(symbol: str, request: Request, quarter: str | None = None):  # a path segment: the web proxy forwards no query string
    """Vì sao lợi nhuận quý thay đổi: a watched non-financial ticker's parent profit, same quarter last year to this one."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    symbol, data_dir = symbol.upper(), Path(data_dir)
    if not _SYMBOL.fullmatch(symbol) or symbol not in load_watchlist(data_dir).symbols:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    if quarter is not None and not _QUARTER.fullmatch(quarter):
        return error(422, "invalid_quarter", "Quý theo dạng YYYY-Qn.")
    if kind_of(load_sectors(data_dir)[0].get(symbol)) is not None:
        return {"symbol": symbol, "financial": True, "quarters": [], "bridge": None}
    quarters = (StatementStore(data_dir / "statements").read(symbol) or {}).get("quarters") or {}
    usable = sorted((q for q in quarters if f"{int(q[:4]) - 1}{q[4:]}" in quarters), reverse=True)
    pick = quarter or (usable[0] if usable else None)
    return {"symbol": symbol, "financial": False, "quarters": usable, "bridge": profit_bridge(quarters, pick) if pick else None}
