"""Thuyết minh TSCĐ nhập tay on a watched non-financial company's page: the owner's construction projects and depreciation ranges,
kept in a settings record per ticker; the due quarter moves only by a postponement."""

import re
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.fixed_asset_notes import (GROUPS, MAX_DEALS, MAX_PROJECTS, PREPAID_KINDS, NoteError, complete, deals_view, due_view,
                                                         postpone, prepaid_view, validate_deals, validate_notes, validate_prepaid)
from investment_agent.domain.models import ContractModel
from investment_agent.market.financial_ratios import kind_of
from investment_agent.market.sectors import load_sectors
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.fixed_asset_notes import read_notes, record_id

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal")
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
_REQUEST = r"^[A-Za-z0-9_-]{1,128}$"
NOT_A_COMPANY = "Chỉ ghi thuyết minh TSCĐ cho doanh nghiệp (không phải ngân hàng, chứng khoán, bảo hiểm) trong danh sách theo dõi."


class NotesRequest(ContractModel):
    projects: list[dict] = Field(max_length=MAX_PROJECTS)
    ranges: dict
    prepaid: dict | None = None  # left out: the stored allocation is kept
    deals: list[dict] | None = Field(default=None, max_length=MAX_DEALS)  # left out: the stored deals are kept
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=_REQUEST)


class PostponeRequest(ContractModel):
    id: str = Field(max_length=32)
    to: str = Field(max_length=10)
    reason: str = Field(default="", max_length=200)
    expected_version: int = Field(strict=True, ge=1)
    request_id: str = Field(pattern=_REQUEST)


class CompleteRequest(ContractModel):
    id: str = Field(max_length=32)
    expected_version: int = Field(strict=True, ge=1)
    request_id: str = Field(pattern=_REQUEST)


def _company(request: Request, symbol: str) -> str | None:
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return None
    symbol = symbol.upper()
    ok = _SYMBOL.fullmatch(symbol) and symbol in load_watchlist(Path(data_dir)).symbols and kind_of(load_sectors(Path(data_dir))[0].get(symbol)) is None
    return symbol if ok else None


def _today(request: Request):
    return now(request).astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date()


def _view(request: Request, repo, owner, symbol: str) -> dict:
    record, projects, ranges = read_notes(repo, owner, symbol)
    statements = StatementStore(Path(request.app.state.data_dir) / "statements").read(symbol) or {}
    return {"symbol": symbol, "version": record.version if record else 0, "projects": due_view(projects, statements, today=_today(request)),
            "ranges": ranges, "groups": GROUPS, "prepaid": prepaid_view(_stored(record, "prepaid", {}), statements), "prepaid_kinds": PREPAID_KINDS,
            "deals": deals_view(_stored(record, "deals", []), today=_today(request))}


def _stored(record, key: str, empty):
    return (record.payload if record else {}).get(key, empty)


def _run(request: Request, symbol: str, change):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    if not (sym := _company(request, symbol)):
        return error(404, "not_a_company", NOT_A_COMPANY)
    try:
        if change is not None:
            change(repo, owner, sym)
        return _view(request, repo, owner, sym)
    except NoteError as exc:
        return error(422, exc.code, exc.message)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    except RepositoryUnavailable:
        return unavailable()


def _write(repo, owner, sym: str, projects: list, ranges: dict, body, prepaid: dict | None = None, deals: list | None = None) -> None:
    """prepaid, deals None: the stored ones are kept."""
    record = read_notes(repo, owner, sym)[0]
    prepaid = _stored(record, "prepaid", {}) if prepaid is None else prepaid
    deals = _stored(record, "deals", []) if deals is None else deals
    repo.write(owner, "settings", record_id(sym), {"symbol": sym, "projects": projects, "ranges": ranges, "prepaid": prepaid, "deals": deals},
               expected_version=body.expected_version, request_id=body.request_id)


@router.get("/stock/{symbol}/fixed-asset-notes")
def get_notes(symbol: str, request: Request):
    return _run(request, symbol, None)


@router.put("/stock/{symbol}/fixed-asset-notes")
def put_notes(symbol: str, request: Request, body: NotesRequest):
    def change(repo, owner, sym):
        _, stored, _ = read_notes(repo, owner, sym)
        projects, ranges = validate_notes(body.projects, body.ranges, stored=stored)
        _write(repo, owner, sym, projects, ranges, body, None if body.prepaid is None else validate_prepaid(body.prepaid),
               None if body.deals is None else validate_deals(body.deals))
    return _run(request, symbol, change)


@router.post("/stock/{symbol}/fixed-asset-notes/postpone")
def postpone_project(symbol: str, request: Request, body: PostponeRequest):
    def change(repo, owner, sym):
        _, stored, ranges = read_notes(repo, owner, sym)
        _write(repo, owner, sym, postpone(stored, body.id, body.to, body.reason, today=_today(request)), ranges, body)
    return _run(request, symbol, change)


@router.post("/stock/{symbol}/fixed-asset-notes/complete")
def complete_project(symbol: str, request: Request, body: CompleteRequest):
    def change(repo, owner, sym):
        _, stored, ranges = read_notes(repo, owner, sym)
        _write(repo, owner, sym, complete(stored, body.id, today=_today(request)), ranges, body)
    return _run(request, symbol, change)
