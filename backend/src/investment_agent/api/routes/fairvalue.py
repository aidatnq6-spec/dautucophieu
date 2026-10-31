"""Reference valuation of the watched tickers (Định giá page): computed on request from stored statements."""

from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.market.beta import BetaStore
from investment_agent.market.company_people import PeopleStore, company_people
from investment_agent.market.financial_ratios import DISPLAY, FinancialRatioStore
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.index_valuation import INDICES, series_key
from investment_agent.market.leading import MacroStore
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.holdings_view import fair_value_board
from investment_agent.services.records import read_version, valuation_settings
from investment_agent.valuation.capm import capm
from investment_agent.valuation.dividend_history import dividend_history
from investment_agent.valuation.forward import Assumptions, forward_valuation
from investment_agent.valuation.history import monthly_multiples
from investment_agent.valuation.index_reference import index_monthly_multiples
from investment_agent.valuation.reference import _d, metrics

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error
from .watchlist import held_tickers

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
QUARTERS_SHOWN = 8


@router.get("/fairvalue")
def fairvalue(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir = request.app.state.data_dir
    if repo is None or data_dir is None:
        return unavailable()
    try:
        board = fair_value_board(data_dir, request.app.state.market, repo, owner, held=held_tickers(request),
                                 today=now(request).astimezone(VN).date())
    except RepositoryUnavailable:
        return unavailable()
    for row in board["rows"]:
        for m in row["methods"]:
            m["value"] = str(m["value"]) if m["value"] is not None else None
    return board


@router.get("/fairvalue/history/{symbol}")
def fairvalue_history(symbol: str, request: Request):
    """Monthly P/E and P/B of one watched ticker or of VNINDEX/VN30 (public statements, prices and index multiples only)."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    data_dir, symbol = Path(data_dir), symbol.upper()
    if symbol in INDICES:
        multiples = SeriesStore(data_dir / "index-valuation")
        return index_monthly_multiples(symbol, pe=multiples.read(series_key(symbol, "pe")), pb=multiples.read(series_key(symbol, "pb")))
    if symbol not in load_watchlist(data_dir).symbols:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    out = monthly_multiples(FundamentalsStore(data_dir / "fundamentals").read(symbol), SeriesStore(data_dir / "trend-sources").read(f"{symbol}-1d"),
                            today=now(request).astimezone(VN).date())
    return {"symbol": symbol, **out}


class ForwardRequest(ContractModel):
    assumptions: Assumptions
    custom: dict[str, str | None] = Field(default_factory=dict)
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _forward_id(symbol: str) -> str:
    return f"forward_{symbol}"


def _forward_view(request: Request, data_dir: Path, symbol: str, record) -> dict:
    """The saved scenario priced on today's base figures and the ticker's monthly P/E and P/B bands."""
    today = now(request).astimezone(VN).date()
    fundamentals = FundamentalsStore(data_dir / "fundamentals").read(symbol)
    m = metrics(fundamentals, today=today, year_end_prices={}) if fundamentals and fundamentals.get("years") else None
    latest = fundamentals["years"].get(m["latest_year"], {}) if m else {}
    point = request.app.state.market.price(symbol) if request.app.state.market else None
    base = {"year": m["latest_year"] if m else None, "profit": _d(latest.get("npat")), "equity": _d(latest.get("equity")),
            "shares": m["shares"] if m else None, "price": point.price if point else None}
    history = monthly_multiples(fundamentals, SeriesStore(data_dir / "trend-sources").read(f"{symbol}-1d"), today=today)
    bands = {k: {"median": history[k]["median"], "sd": history[k]["sd"]} for k in ("pe", "pb")}
    saved = record.payload if record else None
    if saved is None:  # nothing saved yet: base figures and reason only, no forward years
        priced = forward_valuation(base, bands, Assumptions(profit_growth=["0"], equity_growth=["0"], dilution=["0"]))
        priced["years"] = []
    else:
        priced = forward_valuation(base, bands, Assumptions.model_validate(saved["assumptions"]), custom=saved.get("custom") or None)
    return {"symbol": symbol, "version": record.version if record else 0, "assumptions": saved["assumptions"] if saved else None,
            "custom": (saved or {}).get("custom") or {}, "bands": bands, **priced}


def _forward_symbol(request: Request, symbol: str):
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return None, None
    symbol = symbol.upper()
    return (Path(data_dir), symbol) if symbol in load_watchlist(Path(data_dir)).symbols else (Path(data_dir), None)


@router.get("/fairvalue/forward/{symbol}")
def forward_get(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir, sym = _forward_symbol(request, symbol)
    if data_dir is None or repo is None:
        return unavailable()
    if sym is None:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    try:
        return _forward_view(request, data_dir, sym, read_version(repo, owner, "settings", _forward_id(sym), None))
    except RepositoryUnavailable:
        return unavailable()


@router.put("/fairvalue/forward/{symbol}")
def forward_put(symbol: str, request: Request, body: ForwardRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir, sym = _forward_symbol(request, symbol)
    if data_dir is None or repo is None:
        return unavailable()
    if sym is None:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    custom = {}
    for key in ("pe", "pb"):
        raw = (body.custom.get(key) or "").strip()
        if raw:
            d = _d(raw)
            if d is None or d <= 0 or d > 1000:
                return error(422, "invalid_multiple", f"{key.upper()} giả sử phải là số dương.")
            custom[key] = format(d.normalize(), "f")
    try:
        repo.write(owner, "settings", _forward_id(sym), {"assumptions": body.assumptions.model_dump(), "custom": custom},
                   expected_version=body.expected_version, request_id=body.request_id)
        return _forward_view(request, data_dir, sym, read_version(repo, owner, "settings", _forward_id(sym), None))
    except WRITE_ERRORS as exc:
        return write_error(exc)


@router.get("/fairvalue/ratios/{symbol}")
def sector_ratios(symbol: str, request: Request):
    """Quarterly sector ratios of a watched bank, securities firm or insurer (VNDirect public data), oldest quarter first."""
    require_owner(request)
    data_dir, sym = _forward_symbol(request, symbol)
    if data_dir is None:
        return unavailable()
    record = FinancialRatioStore(data_dir / "financial-ratios").read(sym) if sym else None
    if not record or record.get("kind") not in DISPLAY:
        return error(404, "not_a_financial", "Chỉ có cho ngân hàng, chứng khoán, bảo hiểm trong danh sách theo dõi.")
    quarters = sorted(record["quarters"])[-QUARTERS_SHOWN:]
    return {"symbol": sym, "kind": record["kind"], "fetched_at": record.get("fetched_at"),
            "quarters": [{"date": q, "label": f"Q{(int(q[5:7]) + 2) // 3}/{q[:4]}"} for q in quarters],
            "metrics": [{"code": code, "label": label, "format": fmt, "values": [record["quarters"][q].get(code) for q in quarters]}
                        for code, label, fmt in DISPLAY[record["kind"]]]}


@router.get("/fairvalue/dividends/{symbol}")
def dividends(symbol: str, request: Request):
    """Cash and stock dividends by year, payout against the previous year's EPS, and the trailing yield on today's price."""
    require_owner(request)
    data_dir, sym = _forward_symbol(request, symbol)
    if data_dir is None:
        return unavailable()
    if sym is None:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    point = request.app.state.market.price(sym) if request.app.state.market else None
    return {"symbol": sym, **dividend_history(FundamentalsStore(data_dir / "fundamentals").read(sym), price=point.price if point else None,
                                              today=now(request).astimezone(VN).date())}


CAPM_RECORD = ("settings", "capm")


class CapmRequest(ContractModel):
    erp: str = Field(max_length=8)
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _capm_view(request: Request, data_dir: Path, record, beta: dict | None) -> dict:
    """Ke = Rf + β × ERP with each input and its date, next to the owner's required return (a hint, never applied)."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    points = MacroStore(data_dir).read("vn10y")
    rf = {"value": points[-1]["value"], "date": points[-1]["date"]} if points else None
    erp = record.payload.get("erp") if record else None
    settings, _ = valuation_settings(repo, owner)
    return {"version": record.version if record else 0, "rf": rf, "beta": beta, "erp": erp,
            "required_return": str(settings.required_return),
            **capm(rf=rf["value"] if rf else None, beta=beta["value"] if beta else None, erp=erp)}


@router.get("/fairvalue/capm")
def capm_market(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    try:
        return _capm_view(request, Path(request.app.state.data_dir), read_version(repo, owner, *CAPM_RECORD, None), {"value": "1", "date": None})
    except RepositoryUnavailable:
        return unavailable()


@router.get("/fairvalue/capm/{symbol}")
def capm_ticker(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir, sym = _forward_symbol(request, symbol)
    if data_dir is None or repo is None:
        return unavailable()
    if sym is None:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    stored = BetaStore(data_dir).read()["values"].get(sym)
    try:
        return _capm_view(request, data_dir, read_version(repo, owner, *CAPM_RECORD, None),
                          {"value": stored["beta"], "date": stored["date"]} if stored else None)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/fairvalue/capm")
def capm_save(request: Request, body: CapmRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    try:
        erp = Decimal(body.erp.strip().replace(",", "."))
    except InvalidOperation:
        erp = None
    if erp is None or not erp.is_finite() or not Decimal(0) < erp <= Decimal(30):
        return error(422, "invalid_erp", "Phần bù rủi ro (ERP) là số phần trăm từ 0 đến 30, ví dụ 7,8.")
    try:
        repo.write(owner, *CAPM_RECORD, {"erp": format(erp.normalize(), "f")}, expected_version=body.expected_version, request_id=body.request_id)
        return _capm_view(request, Path(request.app.state.data_dir), read_version(repo, owner, *CAPM_RECORD, None), {"value": "1", "date": None})
    except WRITE_ERRORS as exc:
        return write_error(exc)


def _fetch_people(symbol: str) -> dict:
    from investment_agent.market.providers.vnstock_adapter import VnstockProvider
    return VnstockProvider().company_people(symbol)


@router.get("/fairvalue/people/{symbol}")
def people(symbol: str, request: Request):
    """Major shareholders and officers (Vnstock, VCI), cached 30 days; the saved copy when the source fails."""
    require_owner(request)
    data_dir, sym = _forward_symbol(request, symbol)
    if data_dir is None:
        return unavailable()
    if sym is None:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    return company_people(PeopleStore(data_dir), sym, fetch=_fetch_people, now=now(request))
