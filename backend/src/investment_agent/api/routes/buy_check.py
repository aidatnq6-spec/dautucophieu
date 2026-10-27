"""Kiểm tra trước khi mua (shown in the trade form before saving a buy): concentration and the asset pyramid after the buy, and a
three-month run-up. Path parameters only: the web proxy signs and forwards the path, not a query string."""

from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.domain.asset_pyramid import asset_pyramid
from investment_agent.domain.buy_check import buy_flags, three_month_change
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.equity_budget import budget_view

from ..auth import require_owner
from .common import error, unavailable
from .concentration import concentration_view

router = APIRouter(prefix="/internal")
FOMO = "0.30"  # +30% in about three months


@router.get("/buy-check/{symbol}/{amount}")
def buy_check(request: Request, symbol: str, amount: str):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    symbol = symbol.strip().upper()
    if not symbol.isalnum() or len(symbol) > 10:
        return error(422, "invalid_symbol", "Mã không hợp lệ.")
    try:
        cost = Decimal(amount)
    except InvalidOperation:
        return error(422, "invalid_amount", "Số tiền không hợp lệ.")
    if not cost.is_finite() or cost <= 0:
        return error(422, "invalid_amount", "Số tiền phải lớn hơn 0.")
    after = concentration_view(request, symbol, format(cost, "f"))
    if not isinstance(after, dict):
        return after  # repository unavailable or invalid input, already a response
    ticker = sector = None
    if after.get("status") == "ok":
        ticker = next((t for t in after["tickers"] if t["symbol"] == symbol), None)
        name = ticker["sector"] if ticker else None
        sector = next((s for s in after["sectors"] if s["sector"] == name and len(s["symbols"]) > 1), None)
    try:
        budget, _ = budget_view(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    warnings, stocks_over = [], False
    if budget.get("status") == "ok" and budget.get("pyramid"):
        amounts = {l["id"]: Decimal(l["amount"]) for l in budget["pyramid"]["layers"]}
        amounts["stocks"] += cost
        amounts["cash"] = amounts.get("cash", Decimal(0)) - cost  # paid from the account's cash
        later = asset_pyramid(amounts, deductions=Decimal(budget["deductions"]), stock_ratio=Decimal(budget["ratio"]))
        warnings = later["warnings"]
        stocks_over = any(l["id"] == "stocks" and l["status"] == "over" for l in later["layers"])
    data_dir = request.app.state.data_dir
    momentum = three_month_change(SeriesStore(Path(data_dir) / "trend-sources").read(f"{symbol}-1d")) if data_dir is not None else None
    flags = buy_flags(ticker=ticker, sector=sector, limit=after.get("limit", "0.25"), pyramid_warnings=warnings, stocks_over=stocks_over,
                      momentum=momentum, fomo=FOMO)
    return {"symbol": symbol, "amount": format(cost, "f"), "flags": flags, "momentum": momentum, "basis": after.get("basis")}
