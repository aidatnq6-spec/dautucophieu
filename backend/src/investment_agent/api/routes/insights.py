"""Nhận định page: verified claims from public reports, aggregated and linked to the watchlist on request (no AI here)."""

import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.insights.store import InsightStore
from investment_agent.insights.summary import link, linking_sectors, summarise
from investment_agent.market.sectors import load_sectors
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.holdings_view import fair_value_board

from ..auth import require_owner
from .common import now, unavailable
from .watchlist import held_tickers

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
WINDOW_DAYS, LISTED_REPORTS = 60, 10


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


@router.get("/insights")
def insights(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir = request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    data_dir, today = Path(data_dir), now(request).astimezone(VN).date()
    try:
        held = held_tickers(request)
        rows = fair_value_board(data_dir, request.app.state.market, repo, owner, held=held, today=today)["rows"]
    except RepositoryUnavailable:
        return unavailable()
    watched = set(load_watchlist(data_dir).symbols)
    sectors = linking_sectors(load_sectors(data_dir)[0], watched=watched, held=held)
    store = InsightStore(data_dir / "insights")
    summary = link(summarise(store.recent(today, days=WINDOW_DAYS)), sectors=sectors, valuation_rows=rows, held=held)
    reports = [{"source": r["source"], "ref_id": r["ref_id"], "title": r["title"], "url": r["page_url"], "published": r["published"],
                "status": r["status"]} for r in store.all()[:LISTED_REPORTS]]
    ssi = _read(data_dir / "insights" / "ssi.json") or {}
    return {"summary": summary, "reports": reports, "ssi": ssi.get("titles", []), "run": _read(data_dir / "insights" / "status.json"),
            "ai_configured": bool(os.environ.get("OPENROUTER_API_KEY")), "window_days": WINDOW_DAYS}
