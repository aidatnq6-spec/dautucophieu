"""Quỹ mở: Fmarket's open-ended funds by kind with their returns beside VN-Index and the 12-month deposit rate, and the owner's fund
rows of Sổ tài sản split by kind (domain.fund_board). Public fund data only reaches Fmarket's side: nothing about the owner is sent."""

import re
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.domain.fund_board import composition, fund_board, funds_holding, look_through
from investment_agent.market.fund_holdings import fund_holdings
from investment_agent.market.fund_nav import FundNavStore, fund_history, fund_profiles
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.deposit_book import read_book
from investment_agent.services.overview import compose_overview

from ..auth import require_owner
from .common import error, now, unavailable

router = APIRouter(prefix="/internal")
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")


def _direct(request: Request, repo, owner) -> tuple[dict[str, Decimal], list[str]]:
    """Market value of each stock held directly; tickers without a price are named, not valued."""
    holdings = compose_overview(repo, owner, request.app.state.market, now(request))["holdings"]
    priced = {h["security_id"]: Decimal(h["market_value"]) for h in holdings if h.get("market_value") is not None}
    return priced, sorted(h["security_id"] for h in holdings if h.get("market_value") is None)


@router.get("/funds")
def get_funds(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        book, _ = read_book(repo, owner)
        direct, unpriced = _direct(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    data_dir = request.app.state.data_dir
    stored = FundNavStore(Path(data_dir)).read() if data_dir is not None else {}
    navs, profiles = stored.get("funds", {}), fund_profiles(data_dir)
    deposits = MacroStore(Path(data_dir)).read("deposit_12m") if data_dir is not None else []
    index = SeriesStore(Path(data_dir) / "trend-sources").points("VNINDEX-1d") if data_dir is not None else []
    bonds = book.bonds if book else ()
    board = fund_board(navs, profiles, index=index, deposit_rate=deposits[-1]["value"] if deposits else None,
                       held={b.fund for b in bonds if b.fund})
    held = fund_holdings(data_dir)
    return {**board, "mine": composition(bonds, navs, profiles), "through": {**look_through(bonds, navs, held, direct=direct), "unpriced": unpriced},
            "source": {"name": stored.get("source"), "fetched_at": stored.get("fetched_at")} if stored else None,
            "history_days": {code: len(points) for code, points in fund_history(data_dir).items()}}


@router.get("/funds/holding/{symbol}")
def get_funds_holding(request: Request, symbol: str):
    """The owner's funds whose published top holdings include this stock (Qua quỹ bạn giữ on the stock page)."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    symbol = symbol.upper()
    if not _SYMBOL.fullmatch(symbol):
        return error(404, "not_found", "Không tìm thấy.")
    try:
        book, _ = read_book(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    data_dir = request.app.state.data_dir
    navs = FundNavStore(Path(data_dir)).read().get("funds", {}) if data_dir is not None else {}
    bonds = book.bonds if book else ()
    return {"symbol": symbol, "funds": funds_holding(symbol, bonds, navs, fund_holdings(data_dir)), "fund_rows": sum(1 for b in bonds if b.fund)}
