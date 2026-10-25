"""Price-only watchlist of the synced tickers; no recommendations."""

from fastapi import APIRouter, Request

from investment_agent.domain.ledger import replay
from investment_agent.market.watchlist import load_watchlist, watchlist_rows
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import LedgerBook

from ..auth import require_owner
from .common import read_version, unavailable

router = APIRouter(prefix="/internal")


@router.get("/watchlist")
def watchlist(request: Request):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        book = LedgerBook(read_version(repo, owner, "ledger_events", "main", None))
    except RepositoryUnavailable:
        return unavailable()
    held = {p.security_id for p in replay(list(book.effective().events)).positions if p.quantity + p.pending_quantity > 0}
    market, wl = request.app.state.market, load_watchlist(request.app.state.data_dir)
    return {"provenance": market.provenance, "groups_as_of": wl.groups_as_of, "rows": watchlist_rows(market, wl, held=held)}
