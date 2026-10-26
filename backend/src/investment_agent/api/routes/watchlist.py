"""Price-only watchlist and market/sector overview of the synced tickers; no recommendations."""

from fastapi import APIRouter, Request

from investment_agent.market.sectors import breadth, index_summary, load_sectors, sector_rows
from investment_agent.market.watchlist import load_watchlist, watchlist_rows
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.holdings_view import held_from_repo

from ..auth import require_owner
from .common import unavailable

router = APIRouter(prefix="/internal")


def held_tickers(request: Request) -> set[str]:
    """Tickers with shares in the owner's ledger; raises RepositoryUnavailable."""
    return held_from_repo(request.app.state.personal_repository, require_owner(request))


def _rows(request: Request):
    """(watchlist, rows) with held flags from the ledger; raises RepositoryUnavailable."""
    wl = load_watchlist(request.app.state.data_dir)
    return wl, watchlist_rows(request.app.state.market, wl, held=held_tickers(request))


@router.get("/watchlist")
def watchlist(request: Request):
    require_owner(request)
    if request.app.state.personal_repository is None:
        return unavailable()
    try:
        wl, rows = _rows(request)
    except RepositoryUnavailable:
        return unavailable()
    return {"provenance": request.app.state.market.provenance, "groups_as_of": wl.groups_as_of, "rows": rows}


@router.get("/market/overview")
def market_overview(request: Request):
    require_owner(request)
    if request.app.state.personal_repository is None:
        return unavailable()
    try:
        wl, rows = _rows(request)
    except RepositoryUnavailable:
        return unavailable()
    sectors, sectors_as_of = load_sectors(request.app.state.data_dir)
    market = request.app.state.market
    return {"provenance": market.provenance, "index": index_summary(market), "breadth": breadth(rows),
            "sectors": sector_rows(rows, sectors), "sectors_as_of": sectors_as_of, "groups_as_of": wl.groups_as_of,
            # GDP, CPI, rates, money supply and FDI are paid-tier data in Vnstock; nothing is estimated in their place.
            "macro": {"available": False, "reason": "source_not_entitled"}}
