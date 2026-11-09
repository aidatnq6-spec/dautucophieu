"""Tháp tài sản theo chu kỳ on Hồ sơ & rủi ro: the owner's mix for each phase of rates, against the layers held now. Reads Tháp tài sản, never feeds it."""

from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.cycle_targets import CycleTargets, compare_mix
from investment_agent.domain.rate_cycle import US, VIETNAM, rate_cycle
from investment_agent.market.leading import MacroStore
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.deposit_book import book_quotes
from investment_agent.services.equity_budget import budget_view
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, now, unavailable, write_error

router = APIRouter(prefix="/internal")
RECORD = ("settings", "cycle_targets")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class TargetsRequest(CycleTargets):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    data_dir = request.app.state.data_dir
    store = MacroStore(data_dir)
    series = {i: [(date.fromisoformat(o["date"]), o["value"]) for o in store.read(i)] for i in (*VIETNAM, *US)}
    cycle = rate_cycle(series, today=now(request).astimezone(VN).date())
    stored = read_version(repo, owner, *RECORD, None)
    targets = CycleTargets.model_validate(stored.payload) if stored else CycleTargets()
    budget, _ = budget_view(repo, owner, quotes=book_quotes(data_dir))
    pyramid = budget.get("pyramid")
    mix = getattr(targets, cycle["phase"]) if cycle["phase"] else None
    reason = "no_phase" if not cycle["phase"] else (budget["status"] if budget["status"] != "ok" else "no_layers") if pyramid is None else "no_target" if mix is None else None
    return {"version": stored.version if stored else 0, "targets": targets.model_dump(mode="json"), "phase": cycle["phase"], "basis": cycle["basis"], "reason": reason,
            "rows": compare_mix(pyramid["layers"], base=Decimal(pyramid["base"]), mix=mix) if reason is None else []}


@router.get("/cycle-targets")
def get_targets(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/cycle-targets")
def put_targets(request: Request, body: TargetsRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    payload = CycleTargets.model_validate(body.model_dump(exclude={"expected_version", "request_id"})).model_dump(mode="json")
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
