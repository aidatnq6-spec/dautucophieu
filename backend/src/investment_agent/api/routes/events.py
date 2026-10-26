"""Lịch sự kiện: corporate events of the watched tickers (public data from data/events), held tickers marked."""

from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.market.corporate_events import REMINDED_KINDS, EventStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable

from ..auth import require_owner
from .common import now, unavailable
from .watchlist import held_tickers

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
AHEAD, BACK, REMIND_DAYS = 60, 30, 5


@router.get("/events")
def events(request: Request):
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    try:
        held = held_tickers(request) if request.app.state.personal_repository is not None else set()
    except RepositoryUnavailable:
        held = set()
    today = now(request).astimezone(VN).date()
    store = EventStore(Path(data_dir))
    symbols = list(load_watchlist(Path(data_dir)).symbols)
    rows = [{**e, "held": e["symbol"] in held} for e in store.events(symbols)]
    ahead, back = (today + timedelta(days=AHEAD)).isoformat(), (today - timedelta(days=BACK)).isoformat()
    main = [e for e in rows if e["kind"] in (*REMINDED_KINDS, "listing", "other")]
    order = lambda e: (e["key_date"] or "", not e["held"], e["symbol"])
    fetched = [d.get("fetched_at") for s in symbols if (d := store.read(s))]
    return {"upcoming": sorted((e for e in main if e["key_date"] and today.isoformat() <= e["key_date"] <= ahead), key=order),
            "recent": sorted((e for e in main if e["key_date"] and back <= e["key_date"] < today.isoformat()), key=order, reverse=True),
            "undated": sorted((e for e in main if not e["key_date"]), key=lambda e: (not e["held"], e["symbol"])),
            "insider": sorted((e for e in rows if e["kind"] == "insider" and e["key_date"] and e["key_date"] >= back), key=order, reverse=True),
            "updated_at": max(fetched) if fetched else None, "remind_days": REMIND_DAYS}
