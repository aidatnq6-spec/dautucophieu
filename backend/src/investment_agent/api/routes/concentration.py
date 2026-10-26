"""Concentration on the Danh mục page: weight of each held ticker and sector (at cost) on the stock budget or investable capital, with a what-if."""

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Request

from investment_agent.domain.concentration import concentration, simulate
from investment_agent.market.sectors import load_sectors
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.equity_budget import budget_view
from investment_agent.services.overview import compose_overview
from investment_agent.services.records import portfolio_settings

from ..auth import require_owner
from .common import error, unavailable
from .common import now as request_now

router = APIRouter(prefix="/internal")


@router.get("/concentration")
def get_concentration(request: Request):
    return _view(request)


@router.get("/concentration/whatif/{symbol}/{amount}")
def what_if(request: Request, symbol: str, amount: str):
    """Path parameters, not a query string: the web proxy signs and forwards the path only."""
    return _view(request, symbol, amount)


def _view(request: Request, symbol: str | None = None, amount: str | None = None):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        view = compose_overview(repo, owner, request.app.state.market, request_now(request))
        settings, _ = portfolio_settings(repo, owner)
        budget, _ = budget_view(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    capital = view["capital"]
    investable = capital["investable_capital"] if capital and capital.get("status") == "ready" else None
    # Once the owner has entered total financial assets, weights are measured on the money set aside for stocks.
    basis = "equity_budget" if budget["status"] == "ok" else "investable_capital"
    if basis == "equity_budget":
        investable = budget["budget"]
    data_dir = request.app.state.data_dir
    sectors = load_sectors(data_dir)[0] if data_dir is not None else {}
    # Valued at cost (what was put in), as the owner chose, so "Còn trống" matches the Hồ sơ page.
    at_cost = [{**h, "market_value": h["total_cost"]} for h in view["holdings"] if h["quantity"] + h["pending_quantity"] > 0]
    base = {**concentration(at_cost, capital=investable, sectors=sectors, limit=settings.concentration_limit), "basis": basis, "valued_at": "cost"}
    if not symbol or amount is None or base["status"] != "ok":
        return base
    try:
        delta = Decimal(amount)
    except InvalidOperation:
        return error(422, "invalid_amount", "Số tiền không hợp lệ.")
    symbol = symbol.strip().upper()
    if not symbol.isalnum() or len(symbol) > 10:
        return error(422, "invalid_symbol", "Mã không hợp lệ.")
    return {**simulate(base, symbol=symbol, amount=delta, sector=sectors.get(symbol)), "what_if": {"symbol": symbol, "amount": str(delta)}}
