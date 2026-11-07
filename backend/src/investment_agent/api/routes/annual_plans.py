"""Kế hoạch năm (ĐHCĐ) on the ticker profile: the owner's revenue and profit plan per year with its source (`settings/annual_plan_<MÃ>`),
CafeF's plan for the years the owner has not entered, and the year-to-date progress from VNDirect's quarters."""

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.annual_plans import plan_progress
from investment_agent.domain.models import ContractModel
from investment_agent.market.plans_cafef import PlanStore
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, unavailable, write_error

router = APIRouter(prefix="/internal/annual-plans")
YEAR = re.compile(r"^20\d{2}$")


class SaveRequest(ContractModel):
    revenue: str = Field(default="", max_length=20)
    profit: str = Field(default="", max_length=20)
    profit_kind: Literal["npat", "npat_parent", "pbt"] = "npat"
    source: str = Field(max_length=300)
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class DeleteRequest(ContractModel):
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def plan_record_id(symbol: str) -> str:
    return f"annual_plan_{symbol}"


def _watched(request: Request, symbol: str) -> str | None:
    data_dir = request.app.state.data_dir
    symbol = symbol.upper()
    return symbol if data_dir is not None and symbol in load_watchlist(Path(data_dir)).symbols else None


def _view(request: Request, record, symbol: str) -> dict:
    plans = (record.payload if record else {}).get("years", {})
    data_dir = Path(request.app.state.data_dir)
    statements = StatementStore(data_dir / "statements").read(symbol)
    cafef = PlanStore(data_dir / "annual-plans-cafef").read(symbol)
    return {"symbol": symbol, "version": record.version if record else 0,
            "plans": plan_progress(plans, statements.get("quarters") if statements else None, cafef=(cafef or {}).get("years"))}


def _amount(raw: str, label: str):
    raw = raw.strip().replace(",", ".")
    if not raw:
        return None, None
    try:
        d = Decimal(raw)
    except InvalidOperation:
        return None, f"{label}: phải là số (tỷ đồng)."
    if not d.is_finite() or d <= 0:
        return None, f"{label}: phải lớn hơn 0."
    return format(d.normalize(), "f"), None


@router.get("/{symbol}")
def get_plans(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    if repo is None:
        return unavailable()
    try:
        return _view(request, read_version(repo, owner, "settings", plan_record_id(sym), None), sym)
    except RepositoryUnavailable:
        return unavailable()


def _change(request: Request, symbol: str, expected_version: int, request_id: str, edit):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record = read_version(repo, owner, "settings", plan_record_id(symbol), None)
        data = edit(dict(record.payload) if record else {"symbol": symbol, "years": {}})
        repo.write(owner, "settings", plan_record_id(symbol), data, expected_version=expected_version, request_id=request_id)
        return _view(request, read_version(repo, owner, "settings", plan_record_id(symbol), None), symbol)
    except WRITE_ERRORS as exc:
        return write_error(exc)


@router.put("/{symbol}/{year}")
def save_plan(symbol: str, year: str, request: Request, body: SaveRequest):
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    if not YEAR.fullmatch(year):
        return error(422, "invalid_year", "Năm theo dạng 2026.")
    revenue, problem = _amount(body.revenue, "Doanh thu kế hoạch")
    profit, problem2 = _amount(body.profit, "Lợi nhuận kế hoạch")
    if problem or problem2:
        return error(422, "invalid_value", problem or problem2)
    if revenue is None and profit is None:
        return error(422, "invalid_value", "Nhập ít nhất doanh thu hoặc lợi nhuận kế hoạch.")
    source = body.source.strip()
    if len(source) < 3:
        return error(422, "invalid_source", "Ghi nguồn của kế hoạch (ví dụ: Nghị quyết ĐHCĐ 2026, ngày họp).")
    plan = {"revenue": revenue, "profit": profit, "profit_kind": body.profit_kind, "source": source}
    return _change(request, sym, body.expected_version, body.request_id, lambda data: {**data, "years": {**data["years"], year: plan}})


@router.post("/{symbol}/{year}/delete")
def delete_plan(symbol: str, year: str, request: Request, body: DeleteRequest):
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    return _change(request, sym, body.expected_version, body.request_id,
                   lambda data: {**data, "years": {y: v for y, v in data["years"].items() if y != year}})
