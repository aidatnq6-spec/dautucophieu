"""Chuỗi giá trị on Thị trường & Ngành: each value chain's sourced stages and how the stored macro series weigh on it now."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.value_chain import factor_status, label, read_indicator, score
from investment_agent.market.leading import MacroStore, load_indicators
from investment_agent.market.value_chains import (CHAIN_MAX_AGE_DAYS, COMMODITY_LABELS, COMMODITY_MAX_AGE_DAYS, VALUE_CHAINS_PATH, fingerprint,
                                                  load_value_chains)
from investment_agent.services import value_chain_approvals as approvals
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable

from ..auth import require_owner
from .common import error, now, unavailable
from .watchlist import held_tickers

router = APIRouter(prefix="/internal/market")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
ORDER = {"tailwind": 0, "neutral": 1, "headwind": 2, "insufficient": 3, None: 4}


class ApprovalRequest(ContractModel):
    approved: bool
    fingerprint: str = Field(pattern=r"^[0-9a-f]{16}$")  # of the content the page showed
    note: str | None = Field(default=None, max_length=approvals.NOTE_MAX)


@router.get("/value-chains")
def value_chains(request: Request):
    require_owner(request)
    if request.app.state.data_dir is None:
        return unavailable()
    return _view(request)


@router.get("/value-chains/returns")
def value_chain_returns(request: Request):
    """Hiệu suất theo kỳ: each chain's members over a week to a year and since January, on stored closes (domain.chain_returns)."""
    from investment_agent.services.flow_board import chain_board
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    config = load_value_chains(getattr(request.app.state, "value_chains_path", VALUE_CHAINS_PATH))
    chains = [{"id": c.id, "name": c.name, "symbols": list(c.symbols)} for c in config.chains]
    return {"chains": chain_board(data_dir, chains, today=now(request).astimezone(VN).date())}


_VALUATION_CACHE: dict = {}  # (data dir, day) -> (computed at, rows): about 2 s to compute, figures change once a day
VALUATION_TTL_SECONDS = 3600


@router.get("/value-chains/valuation")
def value_chain_valuation(request: Request):
    """Định giá chuỗi so với 5 năm: each chain's median P/E and P/B now against its five years (domain.chain_valuation)."""
    import time

    from investment_agent.services.chain_valuation import chain_valuation_board
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    today = now(request).astimezone(VN).date()
    key = (str(data_dir), today)
    hit = _VALUATION_CACHE.get(key)
    if hit and time.monotonic() - hit[0] < VALUATION_TTL_SECONDS:
        return {"chains": hit[1]}
    config = load_value_chains(getattr(request.app.state, "value_chains_path", VALUE_CHAINS_PATH))
    rows = chain_valuation_board(Path(data_dir), [{"id": c.id, "name": c.name, "symbols": list(c.symbols)} for c in config.chains], today=today)
    _VALUATION_CACHE.clear()
    _VALUATION_CACHE[key] = (time.monotonic(), rows)
    return {"chains": rows}


@router.put("/value-chains/{chain_id}/approval")
def set_approval(request: Request, chain_id: str, body: ApprovalRequest):
    """Duyệt or bỏ duyệt one chain; the approval holds for the content the page showed (its fingerprint) and nothing else."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    config = load_value_chains(getattr(request.app.state, "value_chains_path", VALUE_CHAINS_PATH))
    chain = next((c for c in config.chains if c.id == chain_id), None)
    if chain is None:
        return error(404, "chain_not_found", "Không có chuỗi giá trị này.")
    if chain.status == "approved":
        return error(422, "approved_in_config", "Chuỗi này đã duyệt trong tệp cấu hình; đổi trạng thái ở đó.")
    if body.approved and body.fingerprint != fingerprint(config, chain_id):
        return error(409, "content_changed", "Nội dung chuỗi đã đổi từ lúc mở trang; tải lại để đọc bản mới rồi duyệt.")
    if body.approved:
        approvals.approve(Path(data_dir), chain_id, fingerprint=body.fingerprint, note=(body.note or "").strip() or None,
                          on=now(request).astimezone(VN).date())
    else:
        approvals.withdraw(Path(data_dir), chain_id)
    return _view(request)


def _view(request: Request) -> dict:
    data_dir = request.app.state.data_dir
    try:
        held = held_tickers(request) if request.app.state.personal_repository is not None else set()
    except RepositoryUnavailable:
        held = set()
    data_dir, today = Path(data_dir), now(request).astimezone(VN).date()
    config = load_value_chains(getattr(request.app.state, "value_chains_path", VALUE_CHAINS_PATH))
    chains = scored_chains(data_dir, config, today=today, held=held)
    chains.sort(key=lambda c: (ORDER[c["label"]], -(Decimal(c["score"]["good"]) - Decimal(c["score"]["bad"]))))
    covered = {s for c in config.chains for s in c.symbols}
    return {"as_of": today.isoformat(), "chains": chains, "sources": {k: v.model_dump(mode="json") for k, v in config.sources.items()},
            "uncovered": [s for s in load_watchlist(data_dir).symbols if s not in covered]}


def scored_chains(data_dir: Path, config, *, today: date, held: set[str]) -> list[dict]:
    """Each chain with its factors read from the stored macro series, its score and label (None when not approved). A chain is approved
    in the config, or in the app for its current content; an app approval of earlier content shows as stale."""
    indicators = {i["id"]: i for i in load_indicators()}
    store, readings, approved_in_app = MacroStore(data_dir), {}, approvals.read_approvals(data_dir)
    max_age = lambda series: indicators[series]["max_age_days"] if series in indicators else CHAIN_MAX_AGE_DAYS.get(series, COMMODITY_MAX_AGE_DAYS)  # noqa: E731

    def reading(series: str | None) -> dict | None:
        if series is None:
            return None
        if series not in readings:
            points = [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(series)]
            readings[series] = read_indicator(series, points, today=today, max_age_days=max_age(series))
        return readings[series]

    def missing(series: str | None, r: dict | None) -> dict | None:
        """Why a measured factor reads "chưa đánh giá được": no series in the app, no stored figure, a figure past its age, or one figure."""
        if series is None:
            return {"reason": "no_series", "max_age_days": None}
        if r is None:
            return {"reason": "no_data", "max_age_days": max_age(series)}
        if r["stale"]:
            return {"reason": "stale", "max_age_days": max_age(series)}
        if r["direction"] is None:
            return {"reason": "one_point", "max_age_days": max_age(series)}
        return None

    chains = []
    for chain in config.chains:
        factors = []
        for f in chain.factors:
            r = None if f.kind == "event" else reading(f.indicator)
            factors.append({**f.model_dump(mode="json"), "status": "event" if f.kind == "event" else factor_status(f.when_up, r), "reading": r,
                            "missing": None if f.kind == "event" else missing(f.indicator, r),
                            "indicator_label": indicators[f.indicator]["label"] if f.indicator in indicators else COMMODITY_LABELS.get(f.indicator)})
        measured = [(f["weight"], f["status"]) for f in factors if f["status"] != "event"]
        shares = score(measured)
        print_, app = fingerprint(config, chain.id), approved_in_app.get(chain.id)
        if chain.status == "approved":
            approval = {"on": None, "note": None, "by": "config", "stale": False}
        elif app:
            approval = {"on": app["on"], "note": app.get("note"), "by": "app", "stale": app["fingerprint"] != print_}
        else:
            approval = None
        approved = approval is not None and not approval["stale"]
        chains.append({**chain.model_dump(mode="json", exclude={"symbols", "factors"}), "status": "approved" if approved else "draft",
                       "fingerprint": print_, "approval": approval, "factors": factors, "score": shares, "measured": len(measured),
                       # events alone say nothing measurable: too little data, once approved
                       "label": label(shares, approved=approved) if measured else ("insufficient" if approved else None),
                       "symbols": [{"symbol": s, "held": s in held} for s in chain.symbols]})
    return chains


def chain_labels(data_dir: Path, *, today: date, config_path: Path = VALUE_CHAINS_PATH) -> dict[str, list[str | None]]:
    """Labels of the chains each ticker belongs to (tailwind, neutral, headwind, insufficient, or None when not approved)."""
    out: dict[str, list[str | None]] = {}
    for chain in scored_chains(Path(data_dir), load_value_chains(config_path), today=today, held=set()):
        for s in chain["symbols"]:
            out.setdefault(s["symbol"], []).append(chain["label"])
    return out
