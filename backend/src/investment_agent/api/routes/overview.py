"""Overview (decision first, holdings below) and per-entity research views."""

from fastapi import APIRouter, Request

from investment_agent.market.universe import UniverseVersion
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.overview import _s, compose_overview

from ..auth import require_owner
from .common import now as request_now, read_version, unavailable
from .valuation_assumptions import _view as valuation_view

router = APIRouter(prefix="/internal")


@router.get("/overview")
def overview(request: Request):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return compose_overview(repo, owner, request.app.state.market, request_now(request))
    except RepositoryUnavailable:
        return unavailable()


@router.get("/research/{entity_id}")
def research(request: Request, entity_id: str):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    market = request.app.state.market
    try:
        record = read_version(repo, owner, "valuation_assumptions", entity_id, None)
        universe_rec = read_version(repo, owner, "approvals", "universe", None)
    except RepositoryUnavailable:
        return unavailable()
    point = market.price(entity_id)
    universe = UniverseVersion.model_validate(universe_rec.payload) if universe_rec else None
    return {"entity_id": entity_id, "provenance": market.provenance, "industry": market.industry(entity_id),
            "in_universe": bool(universe and entity_id in universe.members),
            "price": {"price": _s(point.price), "session_date": point.session_date.isoformat()} if point else None,
            "evidence": [vars(e) for e in market.evidence(entity_id)], "valuation": valuation_view(record) if record else None,
            "as_of": request_now(request).isoformat()}
