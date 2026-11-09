"""Bảng đèn chỉ báo sớm on a ticker's page: the owner's indicators and thresholds, coloured from stored data."""

from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.market.financial_ratios import kind_of
from investment_agent.market.sectors import load_sectors
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.early_lights import MAX_RULES, catalog, record_id, symbol_lights
from investment_agent.services.weekly_brief import VN

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal/lights")


class Rule(ContractModel):
    id: str = Field(max_length=80)
    bad: str = Field(max_length=30)
    good: str = Field(max_length=30)


class SaveRequest(ContractModel):
    rules: list[Rule] = Field(max_length=MAX_RULES)
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _number(text: str) -> Decimal | None:
    try:
        d = Decimal(text.strip().replace(",", "."))
    except InvalidOperation:
        return None
    return d if d.is_finite() else None


def _context(request: Request, symbol: str):
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return None, None
    data_dir, symbol = Path(data_dir), symbol.upper()
    return data_dir, symbol if symbol in load_watchlist(data_dir).symbols else None


@router.get("/{symbol}")
def get_lights(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir, sym = _context(request, symbol)
    if data_dir is None or repo is None:
        return unavailable()
    if sym is None:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    try:
        return symbol_lights(repo, owner, data_dir, sym, today=now(request).astimezone(VN).date())
    except RepositoryUnavailable:
        return unavailable()


@router.put("/{symbol}")
def save_lights(symbol: str, request: Request, body: SaveRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir, sym = _context(request, symbol)
    if data_dir is None or repo is None:
        return unavailable()
    if sym is None:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    known = {c["id"] for c in catalog(kind_of(load_sectors(data_dir)[0].get(sym)))}
    rules, seen = [], set()
    for r in body.rules:
        bad, good = _number(r.bad), _number(r.good)
        if r.id not in known or r.id in seen:
            return error(422, "invalid_indicator", "Chỉ báo không hợp lệ hoặc bị trùng.")
        if bad is None or good is None or bad == good:
            return error(422, "invalid_threshold", "Ngưỡng Xấu và Tốt phải là số và khác nhau.")
        seen.add(r.id)
        rules.append({"id": r.id, "bad": format(bad.normalize(), "f"), "good": format(good.normalize(), "f")})
    try:
        repo.write(owner, "settings", record_id(sym), {"rules": rules}, expected_version=body.expected_version, request_id=body.request_id)
        return symbol_lights(repo, owner, data_dir, sym, today=now(request).astimezone(VN).date())
    except WRITE_ERRORS as exc:
        return write_error(exc)
