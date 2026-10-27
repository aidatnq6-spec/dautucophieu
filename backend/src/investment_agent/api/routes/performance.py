"""Hiệu quả danh mục: time-weighted performance since the ledger starts, against VN-Index, plus gains by ticker on cost."""

from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.domain.ledger import replay
from investment_agent.domain.time_weighted import benchmarks, performance
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.overview import compose_overview
from investment_agent.services.records import LedgerBook, read_version

from ..auth import require_owner
from .common import now, unavailable

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


@router.get("/performance")
def get_performance(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        events = list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events)
        overview = compose_overview(repo, owner, request.app.state.market, now(request))
    except RepositoryUnavailable:
        return unavailable()
    today = now(request).astimezone(VN).date()
    data_dir = request.app.state.data_dir
    closes, index = {}, {}
    if data_dir is not None:
        store = SeriesStore(Path(data_dir) / "trend-sources")
        symbols = {e.security_id for e in events if getattr(e, "security_id", None)}
        # Daily closes in thousand đồng (Vnstock, adjusted); VN-Index in points.
        closes = {s: {t.date(): v * 1000 for t, v in store.read(f"{s}-1d")} for s in symbols}
        index = {t.date(): v for t, v in store.read("VNINDEX-1d")}
    result = performance(events, closes=closes, index=index, today=today)
    contributions = [{"symbol": h["security_id"], "cost": h["total_cost"], "value": h["market_value"], "unrealized": h["unrealized_gain"]}
                     for h in overview["holdings"]]
    contributions.sort(key=lambda c: abs(float(c["unrealized"])) if c["unrealized"] is not None else -1, reverse=True)
    state = replay(events)
    latest = lambda key: (MacroStore(Path(data_dir)).read(key) or [None])[-1] if data_dir is not None else None  # noqa: E731
    deposit, cpi = latest("deposit_12m"), latest("vn_cpi_yoy")
    bench = benchmarks(result["total"], end=result["series"][-1]["date"] if result["series"] else None,
                       deposit_rate=deposit["value"] if deposit else None, cpi=(cpi["date"], cpi["value"]) if cpi else None)
    return {**result, "benchmarks": bench, "contributions": contributions, "realized_gain": str(state.realized_gain),
            "ledger_started_on": state.started_on.isoformat() if state.started_on else None}
