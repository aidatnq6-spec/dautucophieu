"""Quỹ mở: Fmarket's open-ended funds by kind with their returns beside VN-Index and the 12-month deposit rate, and the owner's fund
rows of Sổ tài sản split by kind (domain.fund_board). Public fund data only reaches Fmarket's side: nothing about the owner is sent."""

from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.domain.fund_board import composition, fund_board
from investment_agent.market.fund_nav import FundNavStore, fund_history, fund_profiles
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.deposit_book import read_book

from ..auth import require_owner
from .common import unavailable

router = APIRouter(prefix="/internal")


@router.get("/funds")
def get_funds(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        book, _ = read_book(repo, owner)
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
    return {**board, "mine": composition(bonds, navs, profiles),
            "source": {"name": stored.get("source"), "fetched_at": stored.get("fetched_at")} if stored else None,
            "history_days": {code: len(points) for code, points in fund_history(data_dir).items()}}
