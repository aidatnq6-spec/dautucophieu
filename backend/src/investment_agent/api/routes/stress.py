"""Kiểm tra sức chịu đựng on Danh mục & Giao dịch: the holdings priced for a shock (the page applies the scenario)."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Request

from investment_agent.domain.sensitivity import SPANS, sensitivity
from investment_agent.domain.stress import stress_inputs
from investment_agent.market.beta import BetaStore
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.drawdown import held_costs, last_close
from investment_agent.services.records import StoredRisk, portfolio_settings, read_version
from investment_agent.services.theses import position_shares

from ..auth import require_owner
from .common import unavailable

router = APIRouter(prefix="/internal")


def _answer10(repo, owner) -> str | None:
    record = read_version(repo, owner, "risk_versions", "main", None)
    if record is None:
        return None
    return next((a.answer for a in StoredRisk.model_validate(record.payload).assessment.answers if a.question == 10), None)


@router.get("/stress")
def stress(request: Request):
    owner, repo, data_dir = require_owner(request), request.app.state.personal_repository, request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    try:
        shares, costs = position_shares(repo, owner), {s: Decimal(c) for s, c in held_costs(repo, owner).items()}
        threshold, answer = portfolio_settings(repo, owner)[0].drawdown_threshold, _answer10(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    series, market, macro = SeriesStore(Path(data_dir) / "trend-sources"), request.app.state.market, MacroStore(data_dir)
    prices = {}
    for symbol in shares:
        point = market.price(symbol) if market is not None else None
        raw = format(point.price, "f") if point is not None else last_close(series, symbol)
        prices[symbol] = None if raw is None else Decimal(raw)
    closes = lambda key: [(t.date(), Decimal(str(v))) for t, v in series.read(key)]  # noqa: E731
    factor = {k: [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in macro.read(f"factor_{k}")] for k in ("oil", "usd")}
    index = closes("VNINDEX-1d")
    sens = {s: sensitivity(closes(f"{s}-1d"), index=index, oil=factor["oil"], usd=factor["usd"], weeks=SPANS["3y"]) for s in shares}
    return stress_inputs(shares=shares, costs=costs, prices=prices, betas=BetaStore(data_dir).read()["values"], sensitivity=sens,
                         index=series.read("VNINDEX-1d"), answer10=answer, threshold=threshold,
                         watched=set(load_watchlist(Path(data_dir)).symbols))
