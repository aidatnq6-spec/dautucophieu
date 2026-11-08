"""Reference valuation of the watched tickers (Định giá page): computed on request from stored statements."""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Path as PathParam, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.market.beta import BetaStore
from investment_agent.market.company_people import PeopleStore, company_people
from investment_agent.market.erp import ErpStore
from investment_agent.market.financial_ratios import DISPLAY, FinancialRatioStore, kind_of
from investment_agent.market.fundamentals import FundamentalsStore
from investment_agent.market.insider_deals import InsiderStore, insider_deals
from investment_agent.market.index_valuation import INDICES, series_key
from investment_agent.market.leading import MacroStore
from investment_agent.market.sectors import load_sectors
from investment_agent.market.series import SeriesStore
from investment_agent.market.statements import StatementStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.holdings_view import fair_value_board
from investment_agent.services.records import read_version, valuation_settings
from investment_agent.valuation.capm import capm
from investment_agent.valuation.dividend_history import dividend_history
from investment_agent.valuation.forward import Assumptions, forward_valuation
from investment_agent.valuation.history import monthly_multiples
from investment_agent.valuation.peer_compare import compare
from investment_agent.valuation.index_reference import index_monthly_multiples
from investment_agent.valuation.bands import percentile_bands
from investment_agent.valuation.milestones import price_milestones
from investment_agent.valuation.sources import merged_fundamentals, valuation_record
from investment_agent.valuation.statement_table import statement_table
from investment_agent.valuation.weekly import weekly_multiples
from investment_agent.valuation.what_if import what_if
from investment_agent.valuation.reference import _d, metrics

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error
from .watchlist import held_tickers

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


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
        check_path = data_dir / "index-valuation" / f"{symbol}-calc-check.json"
        calc = {"pe": multiples.read(f"{symbol}-pe-calc-1d"), "pb": multiples.read(f"{symbol}-pb-calc-1d"),
                "check": json.loads(check_path.read_text(encoding="utf-8"))} if check_path.is_file() else None  # VN-Index only (index-history)
        return index_monthly_multiples(symbol, pe=multiples.read(series_key(symbol, "pe")), pb=multiples.read(series_key(symbol, "pb")), calc=calc)
    if symbol not in load_watchlist(data_dir).symbols:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    today = now(request).astimezone(VN).date()
    v = valuation_record(data_dir, symbol, today=today)
    out = monthly_multiples(v["record"], SeriesStore(data_dir / "trend-sources").read(f"{symbol}-1d"), today=today, shares=v["shares"],
                            published=v["published"])
    return {"symbol": symbol, "source": v["source"], **out}



def _weekly(data_dir: Path, symbol: str, request: Request) -> tuple[str, dict]:
    """The weekly P/E and P/B series on VNDirect's quarters when the ticker has them, the free Vnstock figures otherwise."""
    today = now(request).astimezone(VN).date()
    v = valuation_record(data_dir, symbol, today=today)
    return v["source"], weekly_multiples(v["record"], SeriesStore(data_dir / "trend-sources").read(f"{symbol}-1d"), today=today,
                                         shares=v["shares"], published=v["published"])


@router.get("/fairvalue/weekly/{symbol}")
def fairvalue_weekly(symbol: str, request: Request):
    """Weekly P/E (trailing four quarters) and P/B of one watched ticker, each with its basis and the quarters missing, and their percentile bands."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    data_dir, symbol = Path(data_dir), symbol.upper()
    if symbol not in load_watchlist(data_dir).symbols:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    src, out = _weekly(data_dir, symbol, request)
    return {"symbol": symbol, "source": src, **out, "bands": {k: percentile_bands(out[k]["points"]) for k in ("pe", "pb")}}


@router.get("/fairvalue/whatif/{symbol}/{price}")
def fairvalue_what_if(symbol: str, request: Request, price: int = PathParam(gt=0, le=10_000_000)):
    """Giá giả định: P/E and P/B of one watched ticker at a typed price in đồng, their rank in each window, and the earlier episodes."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    data_dir, symbol = Path(data_dir), symbol.upper()
    if symbol not in load_watchlist(data_dir).symbols:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    src, out = _weekly(data_dir, symbol, request)
    if out["reason"]:
        return {"symbol": symbol, "source": src, "price": str(price), "reason": out["reason"], "pe": None, "pb": None}
    return {"symbol": symbol, "source": src, "price": str(price), "reason": None,
            **{k: what_if(out[k]["points"], shares=out["shares"], price=Decimal(price)) for k in ("pe", "pb")}}


@router.get("/fairvalue/milestones/{symbol}/{threshold}")
def fairvalue_milestones(symbol: str, request: Request, threshold: int = PathParam(ge=5, le=30)):
    """Mốc giá quá khứ of one watched ticker: today against its own past troughs, with the owner's zigzag threshold in percent."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    data_dir, symbol = Path(data_dir), symbol.upper()
    if symbol not in load_watchlist(data_dir).symbols:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    today = now(request).astimezone(VN).date()
    v = valuation_record(data_dir, symbol, today=today)
    out = price_milestones(v["record"], SeriesStore(data_dir / "trend-sources").read(f"{symbol}-1d"), today=today,
                           threshold=Decimal(threshold) / 100, shares=v["shares"], published=v["published"])
    return {"symbol": symbol, "source": v["source"], **out}


@router.get("/fairvalue/statements/{symbol}")
def statements(symbol: str, request: Request):
    """Bảng số tài chính of a watched non-financial ticker: quarterly and yearly tables from VNDirect's statements, with checks."""
    require_owner(request)
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    data_dir, symbol = Path(data_dir), symbol.upper()
    if symbol not in load_watchlist(data_dir).symbols:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    kind = kind_of(load_sectors(data_dir)[0].get(symbol))
    empty = {"symbol": symbol, "kind": kind, "quarters": {"periods": [], "rows": []}, "years": {"periods": [], "rows": []}, "summary": None,
             "checks": [], "conflicts": []}
    table = _table_of(data_dir, symbol, kind)
    if table is None:
        return {**empty, "reason": "Chưa có số liệu VNDirect cho mã này (đồng bộ lúc 20:00, mỗi lượt vài mã)"}
    return {**table, "kind": kind, "reason": None}


def _table_of(data_dir: Path, symbol: str, kind: str | None) -> dict | None:
    """Bảng số tài chính of one ticker from its stored statements; None when none are stored yet."""
    record = StatementStore(data_dir / ("statements" if kind is None else "statements-financial")).read(symbol)
    if record is None:
        return None
    fundamentals = FundamentalsStore(data_dir / "fundamentals").read(symbol)
    return statement_table(record, closes=SeriesStore(data_dir / "trend-sources").read(f"{symbol}-1d"),
                           vnstock=(fundamentals or {}).get("quarters"), kind=kind)


def _period_of(day: str) -> str:
    return f"{day[:4]}-Q{(int(day[5:7]) + 2) // 3}"


@router.get("/fairvalue/peers/{symbol}")
@router.get("/fairvalue/peers/{symbol}/{period}")  # the quarter as a path segment: the web proxy forwards no query string
def peers(symbol: str, request: Request, period: str | None = None):
    """So sánh cùng ngành: every watched ticker of the ticker's sector at one quarter, with the figures its own page shows
    (Bảng số tài chính, Chỉ số ngành, Định giá); the default quarter is the latest one all of them have."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    data_dir = request.app.state.data_dir
    if data_dir is None:
        return unavailable()
    data_dir, symbol = Path(data_dir), symbol.upper()
    watched = load_watchlist(data_dir).symbols
    if symbol not in watched:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    sectors = load_sectors(data_dir)[0]
    sector = sectors.get(symbol)
    group = sorted(s for s in watched if sector and sectors.get(s) == sector)
    base = {"symbol": symbol, "sector": sector, "focus": symbol, "rows": []}
    if sector is None:
        return {**base, "reason": "Chưa rõ ngành của mã này"}
    if len(group) < 2:
        return {**base, "reason": f"Chỉ có 1 mã ngành {sector} trong danh sách theo dõi"}
    kind, today = kind_of(sector), now(request).astimezone(VN).date()
    figures: dict[str, dict[str, dict]] = {}
    current: dict[str, dict] = {}
    for s in group:
        by_period: dict[str, dict] = {}
        table = _table_of(data_dir, s, kind)
        current[s] = (table or {}).get("current") or {}
        for row in (table or {}).get("quarters", {}).get("rows", []):
            if row["key"]:
                for p, v in zip(table["quarters"]["periods"], row["values"]):
                    if v is not None:
                        by_period.setdefault(p, {})[row["key"]] = v
        record = FinancialRatioStore(data_dir / "financial-ratios").read(s) if kind else None
        if record:
            for day, values in record["quarters"].items():
                by_period.setdefault(_period_of(day), {}).update(values)
            if kind == "bank":
                extra, _, _ = _bank_extra_ratios(request, data_dir, s, record["quarters"])
                for day, values in extra.items():
                    by_period.setdefault(_period_of(day), {}).update(values)
        figures[s] = by_period
    board_rows = {}
    if repo is not None:
        try:  # today's fair value and quality from the Định giá board; no holdings are marked here
            board_rows = {r["symbol"]: r for r in fair_value_board(data_dir, request.app.state.market, repo, owner, held=set(), today=today)["rows"]}
        except RepositoryUnavailable:
            board_rows = {}
    today_values = {}
    for s in group:
        row = board_rows.get(s) or {}
        f = ((row.get("quality") or {}).get("f_score")) or {}
        today_values[s] = {"quality": f"{f['score']}/{f['evaluated']}" if f.get("evaluated") else None, "gap": row.get("gap"),
                           "pe_now": current[s].get("pe"), "pb_now": current[s].get("pb")}
    price_date = max((c["close_date"] for c in current.values() if c.get("close_date")), default=None)
    return {**base, **compare(kind, figures, today_values, focus=symbol, period=period), "sector": sector, "reason": None, "price_date": price_date}

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
    fundamentals, _ = merged_fundamentals(data_dir, symbol)
    m = metrics(fundamentals, today=today, year_end_prices={}) if fundamentals and fundamentals.get("years") else None
    latest = fundamentals["years"].get(m["latest_year"], {}) if m else {}
    point = request.app.state.market.price(symbol) if request.app.state.market else None
    base = {"year": m["latest_year"] if m else None, "profit": _d(latest.get("npat")), "equity": _d(latest.get("equity")),
            "shares": m["shares"] if m else None, "price": point.price if point else None}
    v = valuation_record(data_dir, symbol, today=today)
    history = monthly_multiples(v["record"], SeriesStore(data_dir / "trend-sources").read(f"{symbol}-1d"), today=today, shares=v["shares"],
                                published=v["published"])
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


# A bank's ratios VNDirect does not publish: from the notes on Vietcap (data/bank-notes), and from the owner's Số liệu ngân hàng
# (nhập tay) in the quarters entered there. Each is placed after the ratio it reads with; then its decimal places and short name.
# CAR is Vietcap's year-end figure, in the Q4 column (no free source gives it by quarter).
MANUAL_BANK = (("GROUP2_RATIO", "Tỷ lệ nợ nhóm 2", "pct2", "group2_ratio", "BAD_LOANS_RATIO_AQ", 2, "Tỷ lệ nợ nhóm 2"),
               ("CASA", "CASA", "pct1", "casa", "NET_INTEREST_MARGIN_TR_AVG5Q", 1, "CASA"),
               ("CAR", "CAR (cuối năm)", "pct2", "car", "EQUITY_TO_ASSET_AQ", 2, "CAR"))
CAR_GAP = Decimal("0.001")  # Vietcap and VNDirect further apart than 0,1 point: both are listed
CAR_PLACEHOLDER = Decimal("0.08")  # VNDirect gives BID 8,00% year after year: the legal floor, not a reported figure
_QUARTER_END = {"1": "03-31", "2": "06-30", "3": "09-30", "4": "12-31"}


def _entered_bank_ratios(request: Request, sym: str) -> dict[str, dict[str, str]]:
    """{quarter-end date: {code: ratio}} from the quarters the owner entered; none when the store cannot be read."""
    from investment_agent.domain.bank_figures import derive

    from .bank_figures import bank_record_id
    repo = request.app.state.personal_repository
    if repo is None:
        return {}
    try:
        record = read_version(repo, require_owner(request), "settings", bank_record_id(sym), None)
    except RepositoryUnavailable:
        return {}
    out = {}
    for quarter, entry in ((record.payload if record else {}).get("quarters") or {}).items():
        derived = derive(entry.get("values") or {})
        row = {code: derived[key] for code, _, _, key, _, _, _ in MANUAL_BANK if derived.get(key) is not None}
        if row:
            out[f"{quarter[:4]}-{_QUARTER_END[quarter[-1]]}"] = row
    return out


def _quarter_label(day: str) -> str:
    return f"Q{(int(day[5:7]) + 2) // 3}/{day[:4]}"


def _pct(value: str, places: int) -> str:
    return f"{Decimal(value) * 100:.{places}f}".replace(".", ",") + "%"


def _year_end_car(car_years: dict[str, str], vndirect: dict[str, dict]) -> tuple[dict[str, str], list[str]]:
    """{year-end date: CAR} from Vietcap, VNDirect's where Vietcap has no year (never its 8% placeholder); notes where the two differ
    or where Vietcap repeats the year before exactly."""
    out, notes = {}, []
    years = sorted(set(car_years) | {d[:4] for d, row in vndirect.items() if d.endswith("-12-31") and "BANK_CAR_AQ" in row})
    for year in years:
        vc = car_years.get(year)
        vd = (vndirect.get(f"{year}-12-31") or {}).get("BANK_CAR_AQ")
        vd = None if vd is None or Decimal(vd) == CAR_PLACEHOLDER else vd
        if vc is not None:
            out[f"{year}-12-31"] = vc
            if vd is not None and abs(Decimal(vc) - Decimal(vd)) > CAR_GAP:
                notes.append(f"{year} · CAR Vietcap {_pct(vc, 2)} so với VNDirect {_pct(vd, 2)}; bảng dùng số Vietcap.")
            if (before := car_years.get(str(int(year) - 1))) is not None and Decimal(before) == Decimal(vc):
                notes.append(f"{year} · CAR Vietcap {_pct(vc, 2)} trùng đúng năm {int(year) - 1}; kiểm tra lại với báo cáo.")
        elif vd is not None:
            out[f"{year}-12-31"] = vd
    return out, notes


def _bank_extra_ratios(request: Request, data_dir: Path, sym: str, vndirect: dict[str, dict]) -> tuple[dict[str, dict[str, str]], list[str], str | None]:
    """{quarter-end date: {code: ratio}} from Vietcap's notes with the owner's entered quarters on top; notes on every blank or
    difference; when the notes were read."""
    from investment_agent.market.bank_notes import BankNoteStore, note_ratios
    record = BankNoteStore(data_dir / "bank-notes").read(sym) or {}
    out, notes = {}, []
    for day, quarter in sorted((record.get("quarters") or {}).items()):
        ratios, problems = note_ratios(quarter)
        if row := {code: ratios[key] for code, _, _, key, _, _, _ in MANUAL_BANK if key in ratios}:
            out[day] = row
        notes += [f"{_quarter_label(day)} · Vietcap: {p}; để trống." for p in problems]
    car, car_notes = _year_end_car(record.get("car_years") or {}, vndirect)
    for day, value in car.items():
        out.setdefault(day, {})["CAR"] = value
    notes += car_notes
    for day, entered in sorted(_entered_bank_ratios(request, sym).items()):
        for code, _, _, _, _, places, label in MANUAL_BANK:
            if code not in entered:
                continue
            other = out.get(day, {}).get(code)
            if other is not None and Decimal(other) != Decimal(entered[code]):
                notes.append(f"{_quarter_label(day)} · {label} nhập tay {_pct(entered[code], places)} so với Vietcap {_pct(other, places)}; "
                             "bảng dùng số nhập tay.")
            out.setdefault(day, {})[code] = entered[code]
    return out, notes, record.get("fetched_at")


@router.get("/fairvalue/ratios/{symbol}")
def sector_ratios(symbol: str, request: Request):
    """Quarterly sector ratios of a watched bank, securities firm or insurer (VNDirect public data), oldest quarter first; for a
    bank also CASA and the group-2 share, from Vietcap's notes and the quarters the owner entered (those first), with notes on
    every quarter left blank or entered differently."""
    require_owner(request)
    data_dir, sym = _forward_symbol(request, symbol)
    if data_dir is None:
        return unavailable()
    record = FinancialRatioStore(data_dir / "financial-ratios").read(sym) if sym else None
    if not record or record.get("kind") not in DISPLAY:
        return error(404, "not_a_financial", "Chỉ có cho ngân hàng, chứng khoán, bảo hiểm trong danh sách theo dõi.")
    data = {q: dict(v) for q, v in record["quarters"].items()}
    rows, notes, notes_fetched_at = list(DISPLAY[record["kind"]]), [], None
    if record["kind"] == "bank":
        extra, notes, notes_fetched_at = _bank_extra_ratios(request, data_dir, sym, record["quarters"])
        for day, values in extra.items():
            data.setdefault(day, {}).update(values)
        for code, label, fmt, _, after, _, _ in MANUAL_BANK:
            rows.insert(next(i for i, r in enumerate(rows) if r[0] == after) + 1, (code, label, fmt))
    quarters = sorted(data)  # all of them: Bảng số tài chính picks how many to show
    return {"symbol": sym, "kind": record["kind"], "fetched_at": record.get("fetched_at"),
            "quarters": [{"date": q, "label": f"Q{(int(q[5:7]) + 2) // 3}/{q[:4]}"} for q in quarters],
            "metrics": [{"code": code, "label": label, "format": fmt, "values": [data[q].get(code) for q in quarters]} for code, label, fmt in rows],
            "notes": notes, "notes_fetched_at": notes_fetched_at}


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
    erp: str | None = Field(max_length=8)  # None goes back to Damodaran's premium for Vietnam
    expected_version: int = Field(ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _percent(ratio: str | None) -> str | None:
    return format((Decimal(ratio) * 100).normalize(), "f") if ratio else None


def _capm_view(request: Request, data_dir: Path, record, beta: dict | None) -> dict:
    """Ke = Rf + β × ERP with each input and its date, next to the owner's required return (a hint, never applied)."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    points = MacroStore(data_dir).read("vn10y")
    rf = {"value": points[-1]["value"], "date": points[-1]["date"]} if points else None
    owner_erp = record.payload.get("erp") if record else None
    stored = ErpStore(data_dir).read()
    damodaran = {"erp": _percent(stored["erp"]), "erp_cds": _percent(stored.get("erp_cds")), "rating": stored.get("rating"),
                 "published": stored.get("published")} if stored else None
    erp = owner_erp if owner_erp is not None else damodaran["erp"] if damodaran else None
    source = "owner" if owner_erp is not None else "damodaran" if erp is not None else None
    settings, _ = valuation_settings(repo, owner)
    return {"version": record.version if record else 0, "rf": rf, "beta": beta, "erp": erp, "erp_source": source, "owner_erp": owner_erp,
            "damodaran": damodaran, "required_return": str(settings.required_return),
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
    erp = None
    if body.erp is not None:
        try:
            erp = Decimal(body.erp.strip().replace(",", "."))
        except InvalidOperation:
            erp = None
        if erp is None or not erp.is_finite() or not Decimal(0) < erp <= Decimal(30):
            return error(422, "invalid_erp", "Phần bù rủi ro (ERP) là số phần trăm từ 0 đến 30, ví dụ 7,8.")
    try:
        repo.write(owner, *CAPM_RECORD, {"erp": format(erp.normalize(), "f") if erp is not None else None},
                   expected_version=body.expected_version, request_id=body.request_id)
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


def _get_text(url: str) -> str:
    import httpx
    response = httpx.get(url, timeout=30, follow_redirects=False, headers={"User-Agent": "investment-agent/0.1 (personal use)"})
    response.raise_for_status()
    return response.text


@router.get("/fairvalue/insider/{symbol}")
def insider(symbol: str, request: Request):
    """Insider and major-shareholder trade notices (HOSE, via VNDirect), cached a day; the saved copy when the source fails."""
    require_owner(request)
    data_dir, sym = _forward_symbol(request, symbol)
    if data_dir is None:
        return unavailable()
    if sym is None:
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    return insider_deals(InsiderStore(data_dir), sym, get=_get_text, now=now(request))
