"""Leading macro indicators: automatic values from free feeds plus the owner's entries."""

import calendar
from datetime import date as Day
from datetime import timedelta
from datetime import date
from pathlib import Path
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.macro_chain import RATES, macro_chain
from investment_agent.domain.ledger import replay
from investment_agent.domain.liquidity import TERMS, central_view, interbank_view, omo_view
from investment_agent.domain.macro_extras import MAX_EVENTS, EventError, events_view, rate_spread
from investment_agent.market.omo import OmoStore
from investment_agent.market.sectors import load_sectors
from investment_agent.services.macro_events import RECORD as EVENTS_RECORD, merge_events, read_events
from investment_agent.domain.rate_cycle import US, VIETNAM, rate_cycle
from investment_agent.domain.sensitivity import SPANS, exposure, sensitivity
from investment_agent.market.leading import MacroStore, load_indicators, macro_rows
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import LedgerBook, read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal/macro")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


def _is_session(day) -> bool:
    """HOSE's official calendar of that year when the app has it; otherwise every weekday counts (nothing is guessed beyond that)."""
    from investment_agent.cli import load_calendar
    from investment_agent.domain.pinned import CONFIG_DIR
    path = CONFIG_DIR / f"trading-calendar-hose-{day.year}.json"
    if path.is_file():
        try:
            return load_calendar(path).is_session(day)
        except ValueError:
            pass
    return day.weekday() < 5


class ManualObservation(ContractModel):
    date: Day | None = None  # a daily figure: its day (Day: the date type, as the field takes its name)
    month: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # a monthly figure: its month, kept at the month's end
    value: str = Field(min_length=1, max_length=32)
    source_url: str | None = Field(default=None, max_length=500, pattern=r"^https?://\S+$")


def _store(request: Request) -> MacroStore | None:
    data_dir = request.app.state.data_dir
    return MacroStore(data_dir) if data_dir is not None else None


@router.get("")
def macro(request: Request):
    require_owner(request)
    store = _store(request)
    if request.app.state.personal_repository is None or store is None:
        return unavailable()
    today = now(request).astimezone(VN).date()
    return {"as_of": today.isoformat(), "rows": macro_rows(load_indicators(), store, today=today)}


@router.get("/cycle")
def cycle(request: Request):
    """Mốc chu kỳ lãi suất: six-month direction of Vietnam's rates, or the US as a labelled reference until six months are stored."""
    require_owner(request)
    store = _store(request)
    if store is None:
        return unavailable()
    series = {i: [(date.fromisoformat(o["date"]), o["value"]) for o in store.read(i)] for i in (*VIETNAM, *US)}
    return rate_cycle(series, today=now(request).astimezone(VN).date())


@router.get("/chain")
def chain(request: Request):
    """Chuỗi tác động vĩ mô: oil → inflation → rates → foreign flows → VN-Index, each link's direction over about a month."""
    require_owner(request)
    store = _store(request)
    if store is None:
        return unavailable()
    series = {i: [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(i)] for i in ("wti", "vn_cpi_yoy", *RATES, "foreign_net")}
    index = SeriesStore(Path(request.app.state.data_dir) / "trend-sources").read("VNINDEX-1d")
    series["vnindex"] = [(t.date(), Decimal(str(v))) for t, v in index]
    raw = lambda i: [(date.fromisoformat(o["date"]), o["value"]) for o in store.read(i)]  # noqa: E731
    spread = rate_spread(raw("vn_interbank_on"), sofr=raw("sofr"), effr=raw("fed_effr"))["points"]
    series["vnd_usd_spread"] = [(date.fromisoformat(p["date"]), Decimal(p["spread"])) for p in spread]
    today = now(request).astimezone(VN).date()
    omo = _omo(request, store, today)
    latest = omo["latest"]
    chain = macro_chain(series, today=today, omo={"date": latest["date"], "inject": latest["inject"], "absorb": latest["absorb"],
                                                   "net": omo["net"]} if latest else None)
    # watched companies holding net cash of a fifth of their market value or more: a higher deposit rate pays them (public figures)
    from investment_agent.services.cash_rank import cash_rank_rich
    return {**chain, "rate_sensitive": _rate_sensitive(request), "cash_rich": cash_rank_rich(Path(request.app.state.data_dir))}


RATE_SECTORS = ("Ngân hàng", "Bất động sản", "Dịch vụ tài chính")  # ICB names: banks, real estate, securities firms


def _rate_sensitive(request: Request) -> list[dict] | None:
    """The owner's held tickers in the sectors that move most with rates; read here only, never sent anywhere."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return None
    try:
        state = replay(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events))
    except RepositoryUnavailable:
        return None
    sectors = load_sectors(Path(request.app.state.data_dir))[0]
    held = sorted({p.security_id for p in state.positions if p.quantity + p.pending_quantity > 0})
    return [{"symbol": s, "sector": sectors[s]} for s in held if sectors.get(s) in RATE_SECTORS]


def _omo(request: Request, store: MacroStore, today: date) -> dict:
    index = SeriesStore(Path(request.app.state.data_dir) / "trend-sources").read("VNINDEX-1d")
    return omo_view(OmoStore(Path(request.app.state.data_dir)).sessions(), trading_days=[t.date() for t, _ in index], today=today)


@router.get("/liquidity")
def liquidity(request: Request):
    """Thanh khoản và tỷ giá: the central rate and its band, the open market, interbank rates by term, and the month's trade and FDI."""
    require_owner(request)
    store = _store(request)
    if store is None:
        return unavailable()
    today = now(request).astimezone(VN).date()
    dec = lambda i: [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(i)]  # noqa: E731
    last = lambda i: ({"date": o[-1]["date"], "value": o[-1]["value"]} if (o := store.read(i)) else None)  # noqa: E731
    return {"fx": central_view(dec("usd_vnd_central"), vcb=dec("usd_vnd_vcb"), today=today), "omo": _omo(request, store, today),
            "interbank": interbank_view({k: dec(k) for k in TERMS}),
            "external": {k: last(k) for k in ("vn_trade_balance", "vn_trade_balance_ytd", "vn_fdi_disbursed", "vn_fdi_disbursed_yoy")}}


@router.get("/sensitivity")
def sensitivity_view(request: Request):
    return sensitivity_span(request, "3y")


@router.get("/sensitivity/{span}")
def sensitivity_span(request: Request, span: str):
    """Độ nhạy với giá dầu và đồng USD over 3 years, 10 years or every common week: held tickers (largest cost first), then the
    watchlist; computed here on public prices."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if span not in SPANS:
        return error(404, "span_missing", "Khoảng đo phải là 3y, 10y hoặc all.")
    store = _store(request)
    if repo is None or store is None:
        return unavailable()
    try:
        state = replay(list(LedgerBook(read_version(repo, owner, "ledger_events", "main", None)).effective().events))
    except RepositoryUnavailable:
        return unavailable()
    costs = {p.security_id: p.total_cost for p in state.positions if p.quantity + p.pending_quantity > 0}
    factor = {k: [(date.fromisoformat(o["date"]), Decimal(o["value"])) for o in store.read(f"factor_{k}")] for k in ("oil", "usd")}
    prices = SeriesStore(Path(request.app.state.data_dir) / "trend-sources")
    closes = lambda symbol: [(t.date(), Decimal(str(v))) for t, v in prices.read(f"{symbol}-1d")]  # noqa: E731
    index = closes("VNINDEX")
    held = sorted(costs, key=lambda s: costs[s], reverse=True)
    symbols = held + [s for s in load_watchlist(Path(request.app.state.data_dir)).symbols if s not in costs]
    results = {}
    for symbol in symbols:
        results[symbol] = sensitivity(closes(symbol), index=index, oil=factor["oil"], usd=factor["usd"], weeks=SPANS[span])
    return {"span": span, "factors": {k: v[-1][0].isoformat() if v else None for k, v in factor.items()},
            "rows": [{"symbol": s, "held": s in costs, **results[s]} for s in symbols], "exposure": exposure(results, costs)}


@router.get("/spread")
def spread(request: Request):
    """Chênh lệch lãi suất VND–USD: the State Bank's overnight interbank average less SOFR (else EFFR), each stored day."""
    require_owner(request)
    store = _store(request)
    if store is None:
        return unavailable()
    read = lambda i: [(date.fromisoformat(o["date"]), o["value"]) for o in store.read(i)]  # noqa: E731
    return rate_spread(read("vn_interbank_on"), sofr=read("sofr"), effr=read("fed_effr"))


class EventsRequest(ContractModel):
    events: list[dict] = Field(max_length=MAX_EVENTS)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _events_view(request: Request, events: list[dict], version: int) -> dict:
    return {"version": version, **events_view(events, today=now(request).astimezone(VN).date())}


@router.get("/events")
def get_events(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _events_view(request, *read_events(repo, owner))
    except RepositoryUnavailable:
        return unavailable()


@router.put("/events")
def put_events(request: Request, body: EventsRequest):
    """Lịch và nhật ký vĩ mô: the owner's whole list as sent; nothing is filled in from elsewhere."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        events = merge_events(read_events(repo, owner)[0], body.events)
        version = repo.write(owner, *EVENTS_RECORD, {"events": events}, expected_version=body.expected_version, request_id=body.request_id).version
        return _events_view(request, events, version)
    except EventError as exc:
        return error(422, exc.code, exc.message)
    except WRITE_ERRORS as exc:
        return write_error(exc)


@router.post("/{indicator}/observations")
def enter(request: Request, indicator: str, body: ManualObservation):
    require_owner(request)
    store = _store(request)
    if request.app.state.personal_repository is None or store is None:
        return unavailable()
    spec = next((i for i in load_indicators() if i["id"] == indicator), None)
    if spec is None:
        return error(404, "indicator_missing", "Không có chỉ số này.")
    if spec["source"]["kind"] != "manual" and not spec["source"].get("manual_fallback"):
        return error(409, "indicator_automatic", "Chỉ số này được cập nhật tự động, không nhập tay.")
    try:
        value = Decimal(body.value.strip().replace(" ", "").replace(",", "."))
    except InvalidOperation:
        value = None
    if value is None or not value.is_finite():
        return error(422, "invalid_value", "Giá trị phải là một số.")
    # a monthly figure is kept at its month's end, never at the day it was typed (that mixed months up in the trend)
    if spec.get("period") == "month":
        if body.month is None:
            return error(422, "month_required", "Chỉ số theo tháng: chọn tháng của số liệu.")
        y, m = (int(x) for x in body.month.split("-"))
        day = date(y, m, calendar.monthrange(y, m)[1])
        if day > now(request).astimezone(VN).date():
            return error(422, "future_date", "Tháng số liệu chưa kết thúc.")
    else:
        if body.date is None:
            return error(422, "date_required", "Chọn ngày của số liệu.")
        day = body.date
        if day > now(request).astimezone(VN).date():
            return error(422, "future_date", "Ngày số liệu không được ở tương lai.")
        # a figure of the trading session (rates, yields, HOSE's foreign flows and value) is never kept on a day without a session
        if spec.get("period") == "session" and not _is_session(day):
            back = day - timedelta(days=1)
            while not _is_session(back):
                back -= timedelta(days=1)
            return error(422, "not_a_session", f"Ngày {day.strftime('%d/%m/%Y')} là ngày nghỉ, không có phiên giao dịch: chọn phiên gần nhất "
                                                f"({back.strftime('%d/%m/%Y')}).")
    plain = format(value.normalize(), "f")
    store.upsert(indicator, [(day, plain)], entry="manual", source_url=body.source_url)
    return {"indicator": indicator, "date": day.isoformat(), "value": plain}
