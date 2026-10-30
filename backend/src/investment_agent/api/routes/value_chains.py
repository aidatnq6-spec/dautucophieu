"""Chuỗi giá trị on Thị trường & Ngành: each value chain's sourced stages and how the stored macro series weigh on it now."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request

from investment_agent.domain.value_chain import factor_status, label, read_indicator, score
from investment_agent.market.leading import MacroStore, load_indicators
from investment_agent.market.value_chains import COMMODITY_LABELS, COMMODITY_MAX_AGE_DAYS, VALUE_CHAINS_PATH, load_value_chains
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable

from ..auth import require_owner
from .common import now, unavailable
from .watchlist import held_tickers

router = APIRouter(prefix="/internal/market")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
ORDER = {"tailwind": 0, "neutral": 1, "headwind": 2, "insufficient": 3, None: 4}


@router.get("/value-chains")
def value_chains(request: Request):
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    try:
        held = held_tickers(request) if request.app.state.personal_repository is not None else set()
    except RepositoryUnavailable:
        held = set()
    data_dir, today = Path(data_dir), now(request).astimezone(VN).date()
    config = load_value_chains(getattr(request.app.state, "value_chains_path", VALUE_CHAINS_PATH))
    indicators = {i["id"]: i for i in load_indicators()}
    store, readings = MacroStore(data_dir), {}

    def reading(series: str | None) -> dict | None:
        if series is None:
            return None
        if series not in readings:
            points = [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(series)]
            max_age = indicators[series]["max_age_days"] if series in indicators else COMMODITY_MAX_AGE_DAYS
            readings[series] = read_indicator(series, points, today=today, max_age_days=max_age)
        return readings[series]

    chains = []
    for chain in config.chains:
        factors = []
        for f in chain.factors:
            r = reading(f.indicator)
            factors.append({**f.model_dump(mode="json"), "status": factor_status(f.when_up, r), "reading": r,
                            "indicator_label": indicators[f.indicator]["label"] if f.indicator in indicators else COMMODITY_LABELS.get(f.indicator)})
        shares = score([(f["weight"], f["status"]) for f in factors])
        chains.append({**chain.model_dump(mode="json", exclude={"symbols", "factors"}), "factors": factors, "score": shares,
                       "label": label(shares, approved=chain.status == "approved"),
                       "symbols": [{"symbol": s, "held": s in held} for s in chain.symbols]})
    chains.sort(key=lambda c: (ORDER[c["label"]], -(Decimal(c["score"]["good"]) - Decimal(c["score"]["bad"]))))
    covered = {s for c in config.chains for s in c.symbols}
    return {"as_of": today.isoformat(), "chains": chains, "sources": {k: v.model_dump(mode="json") for k, v in config.sources.items()},
            "uncovered": [s for s in load_watchlist(data_dir).symbols if s not in covered]}
