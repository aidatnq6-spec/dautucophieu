"""Luận điểm đầu tư on Danh mục & Giao dịch: the owner's theses with each condition's state, and saving, editing or holding on."""

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.thesis import KINDS, REASON_VI, ThesisError, describe, evaluate
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.theses import company_of, edit, gather, hold, read_theses, save
from investment_agent.services.weekly_brief import VN

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error
from .watchlist import held_tickers

router = APIRouter(prefix="/internal")


def _facts(request: Request, symbols: list[str], today: date) -> dict:
    return gather(Path(request.app.state.data_dir), request.app.state.personal_repository, require_owner(request), symbols, scope="data",
                  today=today, market=request.app.state.market)


def _view(request: Request, theses: list[dict], version: int, held: set[str], today: date) -> dict:
    """Open theses with each condition's state: a broken one stays as recorded; the others are read now from stored data, except
    insider notices, which only the after-close check reads."""
    open_ = [t for t in theses if t["closed_on"] is None]
    facts = _facts(request, sorted({t["symbol"] for t in open_}), today) if request.app.state.data_dir is not None else {}
    shown = []
    for t in open_:
        conds = []
        for c in t["conditions"]:
            if c["status"] == "broken" or c["kind"] == "insider_sell":
                view = {"state": c["status"] or "unknown", "reading": c["current"] or c["reading"],
                        "reason": c["reason"] or (None if c["status"] else "Kiểm sau giờ đóng cửa")}
            else:
                view = evaluate(c, facts.get(t["symbol"], {}))
            conds.append({**c, "label": describe(c), "view": view})
        shown.append({**t, "conditions": conds, "company": company_of(Path(request.app.state.data_dir), t["symbol"])
                      if request.app.state.data_dir is not None else None})
    missing = sorted(held - {t["symbol"] for t in open_})
    companies = {s: company_of(Path(request.app.state.data_dir), s) if request.app.state.data_dir is not None else None for s in missing}
    return {"version": version, "theses": shown, "missing": missing, "companies": companies,
            "kinds": {k: {"label": v[0], "params": list(v[1]), "applies": v[3]} for k, v in KINDS.items()}, "reasons": REASON_VI}


@router.get("/theses")
def get_theses(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        theses, version = read_theses(repo, owner)
        return _view(request, theses, version, held_tickers(request), now(request).astimezone(VN).date())
    except RepositoryUnavailable:
        return unavailable()


class ThesisChange(ContractModel):
    action: str = Field(pattern=r"^(save|edit|hold)$")
    symbol: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2,10}$")
    thesis_id: str | None = Field(default=None, max_length=32)
    cond_id: str | None = Field(default=None, max_length=32)
    reasons: list[str] | None = Field(default=None, max_length=5)
    note: str | None = Field(default=None, max_length=2000)
    conditions: list[dict] | None = Field(default=None, max_length=10)
    reason: str | None = Field(default=None, max_length=2000)
    emotion: str | None = Field(default=None, max_length=16)
    until: date | None = None
    new_condition: dict | None = None
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


@router.put("/theses")
def change_theses(request: Request, body: ThesisChange):
    owner, repo, data_dir = require_owner(request), request.app.state.personal_repository, request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    today = now(request).astimezone(VN).date()
    try:
        held = held_tickers(request)
        theses = read_theses(repo, owner)[0]
        symbol = body.symbol if body.action == "save" else next((t["symbol"] for t in theses if t["id"] == body.thesis_id), None)
        if symbol is None:
            raise ThesisError("thesis_not_found", "Không tìm thấy luận điểm này; hãy tải lại.")
        company = company_of(Path(data_dir), symbol)
        facts = _facts(request, [symbol], today)[symbol]
        fair = None if facts.get("fair") is None else format(facts["fair"].normalize(), "f")
        raw = {"reasons": body.reasons or [], "note": body.note or "", "conditions": body.conditions or []}
        common = {"today": today, "expected_version": body.expected_version, "request_id": body.request_id}
        if body.action == "save":
            theses, version = save(repo, owner, symbol=symbol, raw=raw, company=company, facts=facts, held=held, **common)
        elif body.action == "edit":
            theses, version = edit(repo, owner, thesis_id=body.thesis_id, raw=raw, company=company, fair=fair, **common)
        else:
            theses, version = hold(repo, owner, thesis_id=body.thesis_id, cond_id=body.cond_id or "", reason=body.reason or "", emotion=body.emotion,
                                   until=body.until, new_condition=body.new_condition, company=company, fair=fair, facts=facts, **common)
        return _view(request, theses, version, held, today)
    except ThesisError as exc:
        return error(422, exc.code, exc.message)
    except WRITE_ERRORS as exc:
        return write_error(exc)
