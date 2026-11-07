"""Số liệu vận hành nhập tay on the ticker profile (`settings/operating_<MÃ>`): the owner's groups of operating figures, their periods
with sources, and the totals, shares and growth worked out from them."""

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.bank_figures import UnsafeUrl, check_public_https
from investment_agent.domain.operating import group_view, valid_period
from investment_agent.domain.operating_pdf import propose_values
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, unavailable, write_error

router = APIRouter(prefix="/internal/operating")
GROUP_ID = re.compile(r"^[a-z0-9-]{1,40}$")
MAX_GROUPS = 12


class GroupRequest(ContractModel):
    name: str = Field(min_length=1, max_length=80)
    unit: str = Field(min_length=1, max_length=30)
    period: Literal["month", "quarter", "year"]
    series: list[str] = Field(min_length=1, max_length=12)
    chart: Literal["stack", "line"]
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class ValuesRequest(ContractModel):
    values: dict[str, str]
    source: str = Field(max_length=300)
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class ReadRequest(ContractModel):
    url: str = Field(max_length=500)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class DeleteRequest(ContractModel):
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def record_id(symbol: str) -> str:
    return f"operating_{symbol}"


def _watched(request: Request, symbol: str) -> str | None:
    data_dir = request.app.state.data_dir
    symbol = symbol.upper()
    return symbol if data_dir is not None and symbol in load_watchlist(Path(data_dir)).symbols else None


def _view(record, symbol: str) -> dict:
    groups = (record.payload if record else {}).get("groups", {})
    return {"symbol": symbol, "version": record.version if record else 0, "groups": [group_view(g, groups[g]) for g in sorted(groups)]}


def _change(request: Request, symbol: str, expected_version: int, request_id: str, edit):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record = read_version(repo, owner, "settings", record_id(symbol), None)
        data = dict(record.payload) if record else {"symbol": symbol, "groups": {}}
        data = edit(data)
        if isinstance(data, tuple):  # (status, code, message) from the edit: refused
            return error(*data)
        repo.write(owner, "settings", record_id(symbol), data, expected_version=expected_version, request_id=request_id)
        return _view(read_version(repo, owner, "settings", record_id(symbol), None), symbol)
    except WRITE_ERRORS as exc:
        return write_error(exc)


@router.get("/{symbol}")
def get_operating(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    if repo is None:
        return unavailable()
    try:
        return _view(read_version(repo, owner, "settings", record_id(sym), None), sym)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/{symbol}/groups/{group_id}")
def save_group(symbol: str, group_id: str, request: Request, body: GroupRequest):
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    if not GROUP_ID.fullmatch(group_id):
        return error(422, "invalid_group", "Mã nhóm chỉ gồm chữ thường không dấu, số và gạch ngang.")
    series = [s.strip() for s in body.series]
    if any(not s or len(s) > 40 for s in series) or len(set(series)) != len(series):
        return error(422, "invalid_series", "Tên các dòng phải khác nhau, mỗi tên 1–40 ký tự.")

    def edit(data):
        groups = dict(data.get("groups", {}))
        old = groups.get(group_id, {})
        if group_id not in groups and len(groups) >= MAX_GROUPS:
            return 422, "too_many_groups", f"Tối đa {MAX_GROUPS} nhóm mỗi mã."
        if old and old.get("period") != body.period and old.get("values"):
            return 422, "period_change", "Nhóm đã có số theo kỳ khác; xóa số cũ trước khi đổi kỳ."
        values = {p: {s: v for s, v in vals.items() if s in series} for p, vals in old.get("values", {}).items()}
        groups[group_id] = {"name": body.name.strip(), "unit": body.unit.strip(), "period": body.period, "series": series, "chart": body.chart,
                            "values": values, "sources": old.get("sources", {})}
        return {**data, "groups": groups}
    return _change(request, sym, body.expected_version, body.request_id, edit)


@router.post("/{symbol}/groups/{group_id}/delete")
def delete_group(symbol: str, group_id: str, request: Request, body: DeleteRequest):
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    return _change(request, sym, body.expected_version, body.request_id,
                   lambda data: {**data, "groups": {g: v for g, v in data.get("groups", {}).items() if g != group_id}})


@router.put("/{symbol}/groups/{group_id}/values/{period}")
def save_values(symbol: str, group_id: str, period: str, request: Request, body: ValuesRequest):
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    source = body.source.strip()
    if len(source) < 3:
        return error(422, "invalid_source", "Ghi nguồn của số liệu kỳ này (ví dụ: Bản tin SXKD tháng 10/2026).")

    def edit(data):
        group = data.get("groups", {}).get(group_id)
        if group is None:
            return 404, "group_not_found", "Không có nhóm số liệu này."
        if not valid_period(period, group["period"]):
            return 422, "invalid_period", {"month": "Kỳ theo dạng 2026-09.", "quarter": "Kỳ theo dạng 2026-Q3.", "year": "Kỳ theo dạng 2026."}[group["period"]]
        values = {}
        for s, raw in body.values.items():
            if s not in group["series"]:
                return 422, "unknown_series", f"Nhóm không có dòng “{s}”."
            raw = (raw or "").strip().replace(",", ".")
            if not raw:
                continue
            try:
                d = Decimal(raw)
            except InvalidOperation:
                return 422, "invalid_value", f"{s}: phải là số."
            if not d.is_finite():
                return 422, "invalid_value", f"{s}: phải là số."
            values[s] = format(d.normalize(), "f")
        if not values:
            return 422, "invalid_value", "Nhập ít nhất một số."
        groups = dict(data["groups"])
        groups[group_id] = {**group, "values": {**group.get("values", {}), period: values}, "sources": {**group.get("sources", {}), period: source}}
        return {**data, "groups": groups}
    return _change(request, sym, body.expected_version, body.request_id, edit)


@router.post("/{symbol}/groups/{group_id}/values/{period}/delete")
def delete_values(symbol: str, group_id: str, period: str, request: Request, body: DeleteRequest):
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")

    def edit(data):
        group = data.get("groups", {}).get(group_id)
        if group is None:
            return 404, "group_not_found", "Không có nhóm số liệu này."
        groups = dict(data["groups"])
        groups[group_id] = {**group, "values": {p: v for p, v in group.get("values", {}).items() if p != period},
                            "sources": {p: v for p, v in group.get("sources", {}).items() if p != period}}
        return {**data, "groups": groups}
    return _change(request, sym, body.expected_version, body.request_id, edit)


def _read_pdf(url: str) -> list[str]:
    from .bank_figures import _read_pdf as read  # the same guarded download: https, no redirects, 30 MB, 250 pages
    return read(url)


@router.post("/{symbol}/groups/{group_id}/read-pdf")
def read_pdf(symbol: str, group_id: str, request: Request, body: ReadRequest):
    """Proposed values for the group's lines from a public PDF bulletin; nothing is saved until the owner confirms them."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    if repo is None:
        return unavailable()
    try:
        record = read_version(repo, owner, "settings", record_id(sym), None)
    except RepositoryUnavailable:
        return unavailable()
    group = ((record.payload if record else {}).get("groups") or {}).get(group_id)
    if group is None:
        return error(404, "group_not_found", "Không có nhóm số liệu này.")
    try:
        check_public_https(body.url)
    except UnsafeUrl as exc:
        return error(422, "unsafe_url", str(exc))
    try:
        pages = _read_pdf(body.url)
    except Exception:
        return error(502, "pdf_unavailable", "Không tải được file PDF (kiểm tra đường dẫn, file tối đa 30 MB).")
    return {"url": body.url, **propose_values(pages, group["series"])}
