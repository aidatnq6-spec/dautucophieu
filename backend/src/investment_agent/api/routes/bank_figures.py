"""Số liệu ngân hàng nhập tay on a bank's page: loans by group, deposits and CAR per quarter (`settings/bank_figures_<MÃ>`),
and reading a public PDF of the quarterly statements into proposed values the owner confirms before saving."""

import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.bank_figures import FIELDS, LABELS, UnsafeUrl, check_public_https, derive, parse_report_pages
from investment_agent.domain.models import ContractModel
from investment_agent.market.sectors import load_sectors
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, unavailable, write_error

router = APIRouter(prefix="/internal/bank-figures")
QUARTER = re.compile(r"^\d{4}-Q[1-4]$")
MAX_PDF_BYTES, MAX_PDF_SECONDS, MAX_PDF_PAGES = 30_000_000, 60, 250


class Source(ContractModel):
    kind: Literal["manual", "pdf"]
    url: str | None = Field(default=None, max_length=500)
    pages: dict[str, int] = Field(default_factory=dict)


class SaveRequest(ContractModel):
    values: dict[str, str | None]
    source: Source
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class DeleteRequest(ContractModel):
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class ReadRequest(ContractModel):
    url: str = Field(max_length=500)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def bank_record_id(symbol: str) -> str:
    return f"bank_figures_{symbol}"


def _watched_bank(request: Request, symbol: str) -> str | None:
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return None
    symbol = symbol.upper()
    sectors = load_sectors(Path(data_dir))[0]
    return symbol if symbol in load_watchlist(Path(data_dir)).symbols and sectors.get(symbol) == "Ngân hàng" else None


def bank_view(record, symbol: str) -> dict:
    quarters = (record.payload if record else {}).get("quarters", {})
    rows = [{"quarter": q, "values": v["values"], "derived": derive(v["values"]), "source": v["source"]} for q, v in sorted(quarters.items(), reverse=True)]
    return {"symbol": symbol, "version": record.version if record else 0, "quarters": rows, "labels": LABELS}


def _clean(values: dict[str, str | None]):
    """Whole or decimal non-negative amounts in tỷ đồng (CAR in %, 0–100); empty means missing. Returns (values, problem)."""
    out = {}
    for field in FIELDS:
        raw = (values.get(field) or "").strip()
        if not raw:
            out[field] = None
            continue
        try:
            d = Decimal(raw)
        except InvalidOperation:
            return None, f"{LABELS[field]}: phải là số."
        if not d.is_finite() or d < 0 or (field == "car" and d > 100):
            return None, f"{LABELS[field]}: {'từ 0 đến 100' if field == 'car' else 'không âm'}."
        out[field] = format(d.normalize(), "f")
    if all(v is None for v in out.values()):
        return None, "Nhập ít nhất một số."
    return out, None


def _change(request: Request, symbol: str, expected_version: int, request_id: str, edit):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record = read_version(repo, owner, "settings", bank_record_id(symbol), None)
        data = edit(dict(record.payload) if record else {"symbol": symbol, "quarters": {}})
        repo.write(owner, "settings", bank_record_id(symbol), data, expected_version=expected_version, request_id=request_id)
        return bank_view(read_version(repo, owner, "settings", bank_record_id(symbol), None), symbol)
    except WRITE_ERRORS as exc:
        return write_error(exc)


@router.get("/{symbol}")
def get_bank_figures(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if not (sym := _watched_bank(request, symbol)):
        return error(404, "not_a_watched_bank", "Chỉ nhập cho ngân hàng trong danh sách theo dõi.")
    if repo is None:
        return unavailable()
    try:
        return bank_view(read_version(repo, owner, "settings", bank_record_id(sym), None), sym)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/{symbol}/{quarter}")
def save_quarter(symbol: str, quarter: str, request: Request, body: SaveRequest):
    if not (sym := _watched_bank(request, symbol)):
        return error(404, "not_a_watched_bank", "Chỉ nhập cho ngân hàng trong danh sách theo dõi.")
    if not QUARTER.fullmatch(quarter):
        return error(422, "invalid_quarter", "Quý theo dạng 2026-Q3.")
    values, problem = _clean(body.values)
    if problem:
        return error(422, "invalid_value", problem)
    source = {"kind": body.source.kind, "url": body.source.url, "pages": {k: v for k, v in body.source.pages.items() if k in FIELDS}} \
        if body.source.kind == "pdf" else {"kind": "manual"}
    return _change(request, sym, body.expected_version, body.request_id,
                   lambda data: {**data, "quarters": {**data["quarters"], quarter: {"values": values, "source": source}}})


@router.post("/{symbol}/{quarter}/delete")
def delete_quarter(symbol: str, quarter: str, request: Request, body: DeleteRequest):
    if not (sym := _watched_bank(request, symbol)):
        return error(404, "not_a_watched_bank", "Chỉ nhập cho ngân hàng trong danh sách theo dõi.")
    return _change(request, sym, body.expected_version, body.request_id,
                   lambda data: {**data, "quarters": {q: v for q, v in data["quarters"].items() if q != quarter}})


def _read_pdf(url: str) -> list[str]:
    import httpx

    from investment_agent.insights.download import fetch_pdf
    from investment_agent.insights.pdf import extract_pages
    # No redirects: a redirect could lead to an address check_public_https never saw.
    with httpx.Client(timeout=30, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"}) as client:
        return extract_pages(fetch_pdf(client, url, max_bytes=MAX_PDF_BYTES, max_seconds=MAX_PDF_SECONDS), max_pages=MAX_PDF_PAGES)


@router.post("/{symbol}/read-pdf")
def read_pdf(symbol: str, request: Request, body: ReadRequest):
    """Proposed values from a public PDF; nothing is saved until the owner confirms them."""
    require_owner(request)
    if not _watched_bank(request, symbol):
        return error(404, "not_a_watched_bank", "Chỉ nhập cho ngân hàng trong danh sách theo dõi.")
    try:
        check_public_https(body.url)
    except UnsafeUrl as exc:
        return error(422, "unsafe_url", str(exc))
    try:
        pages = _read_pdf(body.url)
    except Exception:
        return error(502, "pdf_unavailable", "Không tải được file PDF (kiểm tra đường dẫn, file tối đa 30 MB).")
    return {"url": body.url, **parse_report_pages(pages)}
