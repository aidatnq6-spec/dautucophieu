"""Nợ vay ròng and Tiền khách trả trước on a watched non-financial ticker's page, read from its stored public statements; the sector's
borrowing adds up the watched tickers of the same sector. Nothing personal is read."""

import re
from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.domain.balance_watch import borrowing_flag, net_debt_rows, property_cash, sector_debt
from investment_agent.market.financial_ratios import kind_of
from investment_agent.market.sectors import load_sectors
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist

from ..auth import require_owner
from .common import error, unavailable

router = APIRouter(prefix="/internal")
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
PROPERTY = "Bất động sản"


@router.get("/stock/{symbol}/balance")
def balance(symbol: str, request: Request):
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    symbol, data_dir = symbol.upper(), Path(data_dir)
    if not _SYMBOL.fullmatch(symbol):
        return error(400, "invalid_symbol", "Mã cổ phiếu không hợp lệ.")
    watched = load_watchlist(data_dir).symbols
    if symbol not in watched:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    sectors = load_sectors(data_dir)[0]
    sector = sectors.get(symbol)
    if kind_of(sector) is not None:
        return error(404, "not_applicable", "Ngân hàng, chứng khoán và bảo hiểm không đọc nợ vay theo cách này.")
    store = StatementStore(data_dir / "statements")
    record = store.read(symbol)
    quarters = (record or {}).get("quarters", {})
    if not quarters:
        return error(404, "no_statements", "Chưa có báo cáo tài chính của mã này.")
    peers = {s: (store.read(s) or {}).get("quarters", {}) for s in watched if sector and sectors.get(s) == sector}
    peers = {s: qs for s, qs in peers.items() if qs}
    return {"symbol": symbol, "sector": sector, "debt": {"rows": net_debt_rows(quarters), "flag": borrowing_flag(quarters)},
            "sector_debt": {**sector_debt(peers), "members": len(peers)} if sector else None,
            "property": property_cash(quarters) if sector == PROPERTY else None}
