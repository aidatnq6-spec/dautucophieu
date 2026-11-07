"""Dự phóng quý tới in Bảng số tài chính: the owner's assumptions for the quarter after the latest VNDirect quarter
(`settings/quarter_forecast_<MÃ>`), the column they give, and earlier forecasts set beside the figures since reported."""

from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.quarter_forecast import FIELDS, RATES, forecast_quarter, next_quarter
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, unavailable, write_error

router = APIRouter(prefix="/internal/quarter-forecast")
LABELS = {"revenue_yoy": "Doanh thu so cùng kỳ", "gross_margin": "Biên gộp", "selling_pct": "Chi phí bán hàng / doanh thu",
          "admin_pct": "Chi phí quản lý / doanh thu", "fin_income": "Doanh thu tài chính", "fin_expense": "Chi phí tài chính", "interest": "Lãi vay",
          "associates": "LN liên doanh, liên kết", "other_profit": "LN khác", "tax_rate": "Thuế suất", "minority_pct": "Phần cổ đông không kiểm soát",
          "depreciation": "Khấu hao"}
BOUNDS = {"revenue_yoy": (Decimal(-1), Decimal(10)), "gross_margin": (Decimal(-1), Decimal(1))}  # other rates 0–1; amounts any finite number


class SaveRequest(ContractModel):
    assumptions: dict[str, str]
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def record_id(symbol: str) -> str:
    return f"quarter_forecast_{symbol}"


def _quarters(request: Request, symbol: str) -> dict | None:
    rec = StatementStore(Path(request.app.state.data_dir) / "statements").read(symbol)
    return rec.get("quarters") if rec else None


def _watched(request: Request, symbol: str) -> str | None:
    data_dir = request.app.state.data_dir
    symbol = symbol.upper()
    return symbol if data_dir is not None and symbol in load_watchlist(Path(data_dir)).symbols else None


def _view(request: Request, record, symbol: str) -> dict:
    saved = (record.payload if record else {}).get("quarters", {})
    quarters = _quarters(request, symbol)
    base = {"symbol": symbol, "version": record.version if record else 0, "labels": LABELS}
    if not quarters:
        return {**base, "quarter": None, "assumptions": None, "values": {}, "earlier": [],
                "reason": "Chưa có số quý VNDirect của mã này (ngân hàng, chứng khoán, bảo hiểm hoặc mã chưa đồng bộ)"}
    quarter = next_quarter(quarters)
    mine = (saved.get(quarter) or {}).get("assumptions")
    out = forecast_quarter(quarters, quarter, mine) if mine else {"values": {}, "reason": None, "base": None}
    earlier = []
    for q in sorted(saved, reverse=True):
        if q in quarters:
            f = forecast_quarter(quarters, q, saved[q]["assumptions"])["values"]
            earlier.append({"quarter": q, **{k: {"forecast": f.get(k), "actual": quarters[q].get(k)} for k in ("revenue", "npat_parent")}})
    return {**base, "quarter": quarter, "assumptions": mine, "values": out["values"], "base": out.get("base"), "earlier": earlier,
            "reason": out["reason"]}


def _clean(raw: dict[str, str]):
    out = {}
    for key, value in raw.items():
        if key not in FIELDS or value is None or str(value).strip() == "":
            continue
        try:
            d = Decimal(str(value).strip())
        except InvalidOperation:
            return None, f"{LABELS[key]}: phải là số."
        low, high = BOUNDS.get(key, (Decimal(0), Decimal(1))) if key in RATES else (None, None)
        if not d.is_finite() or (low is not None and not low <= d <= high):
            return None, f"{LABELS[key]}: ngoài khoảng cho phép."
        out[key] = format(d.normalize(), "f")
    if not out:
        return None, "Nhập ít nhất một giả định."
    return out, None


@router.get("/{symbol}")
def get_forecast(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    if repo is None:
        return unavailable()
    try:
        return _view(request, read_version(repo, owner, "settings", record_id(sym), None), sym)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/{symbol}/{quarter}")
def save_forecast(symbol: str, quarter: str, request: Request, body: SaveRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    if repo is None:
        return unavailable()
    quarters = _quarters(request, sym)
    if not quarters or quarter != next_quarter(quarters):
        return error(422, "not_the_next_quarter", "Chỉ nhập giả định cho quý ngay sau quý đã có số.")
    assumptions, problem = _clean(body.assumptions)
    if problem:
        return error(422, "invalid_value", problem)
    try:
        record = read_version(repo, owner, "settings", record_id(sym), None)
        data = dict(record.payload) if record else {"symbol": sym, "quarters": {}}
        data["quarters"] = {**data.get("quarters", {}), quarter: {"assumptions": assumptions}}
        repo.write(owner, "settings", record_id(sym), data, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, read_version(repo, owner, "settings", record_id(sym), None), sym)
    except WRITE_ERRORS as exc:
        return write_error(exc)
