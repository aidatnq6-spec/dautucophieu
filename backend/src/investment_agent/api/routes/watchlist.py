"""Price-only watchlist and market/sector overview of the synced tickers; no recommendations."""

from fastapi import APIRouter, Request

from investment_agent.market.sectors import breadth, index_summary, load_sectors, sector_rows
from investment_agent.market.watchlist import load_watchlist, watchlist_rows, vn100_review
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
    return {"provenance": request.app.state.market.provenance, "groups_as_of": wl.groups_as_of, "group_dates": wl.group_dates, "kept": list(wl.kept),
            "vn100_review": vn100_review(wl), "rows": rows}


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


_QUADRANT_INPUTS: dict[str, tuple[tuple, dict]] = {}  # symbol -> (the day and its files' versions, its P/B months and quarters)


@router.get("/watchlist/quadrant")
def watch_quadrant(request: Request):
    """Bong bóng góc phần tư: every watched ticker by its P/B against its own past and its profit growth, sized by what is held."""
    from decimal import Decimal
    from pathlib import Path
    from zoneinfo import ZoneInfo

    from investment_agent.domain.watch_quadrant import quadrant
    from investment_agent.market.financial_ratios import kind_of
    from investment_agent.market.series import SeriesStore
    from investment_agent.market.statements import StatementStore
    from investment_agent.services.overview import compose_overview
    from investment_agent.valuation.history import monthly_multiples
    from investment_agent.valuation.sources import valuation_record

    from .common import now
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir = request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    try:
        holdings = compose_overview(repo, owner, request.app.state.market, now(request))["holdings"]
    except RepositoryUnavailable:
        return unavailable()
    data_dir = Path(data_dir)
    today = now(request).astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    sectors, closes = load_sectors(data_dir)[0], SeriesStore(data_dir / "trend-sources")
    tickers = {}
    for s in load_watchlist(data_dir).symbols:
        folder = "statements" if kind_of(sectors.get(s)) is None else "statements-financial"
        files = [data_dir / "trend-sources" / f"{s}-1d.json", data_dir / "fundamentals" / f"{s}.json", data_dir / "statements" / f"{s}.json",
                 data_dir / folder / f"{s}.json"]
        stamp = (today, folder, tuple((f.stat().st_mtime_ns, f.stat().st_size) if f.is_file() else None for f in files))
        hit = _QUADRANT_INPUTS.get(s)
        if hit and hit[0] == stamp:
            tickers[s] = hit[1]
            continue
        v = valuation_record(data_dir, s, today=today)
        hist = monthly_multiples(v["record"], closes.read(f"{s}-1d"), today=today, shares=v["shares"], published=v["published"])
        store = StatementStore(data_dir / folder)
        tickers[s] = {"pb": [(p["month"], None if p["value"] is None else str(p["value"])) for p in hist["pb"]["points"]],
                      "quarters": (store.read(s) or {}).get("quarters") or {}}
        _QUADRANT_INPUTS[s] = (stamp, tickers[s])  # kept until the day or one of its files changes
    held = {h["security_id"]: Decimal(h["market_value"]) for h in holdings if h.get("market_value") is not None}
    return {**quadrant(tickers, held=held), "sectors": {s: sectors.get(s) for s in tickers}}
