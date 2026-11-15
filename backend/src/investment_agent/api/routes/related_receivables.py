"""Sổ phải thu bên liên quan on the ticker profile: the owner's copy of each year's notes (`settings/related_receivables_<MÃ>`), year by
year, with what a later year stops naming. Public company figures; kept in the owner's store and never sent anywhere."""

import re
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.related_receivables import RelatedError, review, validate_year
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, unavailable, write_error

router = APIRouter(prefix="/internal/related-receivables")
YEAR = re.compile(r"^20\d{2}$")


class SaveRequest(ContractModel):
    source: str = Field(max_length=400)
    rows: list[dict] = Field(max_length=60)
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class DeleteRequest(ContractModel):
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def record_id(symbol: str) -> str:
    return f"related_receivables_{symbol}"


def _watched(request: Request, symbol: str) -> str | None:
    data_dir = request.app.state.data_dir
    symbol = symbol.upper()
    return symbol if data_dir is not None and symbol in load_watchlist(Path(data_dir)).symbols else None


def _view(record, symbol: str) -> dict:
    return {"symbol": symbol, "version": record.version if record else 0, **review((record.payload if record else {}).get("years", {}))}


@router.get("/{symbol}")
def get_book(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    if repo is None:
        return unavailable()
    try:
        return _view(read_version(repo, owner, "settings", record_id(sym), None), sym)
    except RepositoryUnavailable:
        return unavailable()


def _change(request: Request, symbol: str, expected_version: int, request_id: str, edit):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record = read_version(repo, owner, "settings", record_id(symbol), None)
        data = edit(dict(record.payload) if record else {"symbol": symbol, "years": {}})
        repo.write(owner, "settings", record_id(symbol), data, expected_version=expected_version, request_id=request_id)
        return _view(read_version(repo, owner, "settings", record_id(symbol), None), symbol)
    except WRITE_ERRORS as exc:
        return write_error(exc)


@router.put("/{symbol}/{year}")
def save_year(symbol: str, year: str, request: Request, body: SaveRequest):
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    if not YEAR.fullmatch(year):
        return error(422, "invalid_year", "Năm theo dạng 2020.")
    try:
        entry = validate_year(body.source, body.rows)
    except RelatedError as exc:
        return error(422, exc.code, exc.message)
    return _change(request, sym, body.expected_version, body.request_id, lambda data: {**data, "years": {**data["years"], year: entry}})


@router.post("/{symbol}/{year}/delete")
def delete_year(symbol: str, year: str, request: Request, body: DeleteRequest):
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    return _change(request, sym, body.expected_version, body.request_id,
                   lambda data: {**data, "years": {k: v for k, v in data["years"].items() if k != year}})
