"""Leading macro indicators: automatic values from free feeds plus the owner's entries."""

from datetime import date
from pathlib import Path
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.macro_chain import RATES, macro_chain
from investment_agent.domain.ledger import replay
from investment_agent.domain.rate_cycle import US, VIETNAM, rate_cycle
from investment_agent.domain.sensitivity import SPANS, exposure, sensitivity
from investment_agent.market.leading import MacroStore, load_indicators, macro_rows
from investment_agent.market.series import SeriesStore
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import LedgerBook, read_version

from ..auth import require_owner
from .common import error, now, unavailable

router = APIRouter(prefix="/internal/macro")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class ManualObservation(ContractModel):
    date: date
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
    return macro_chain(series, today=now(request).astimezone(VN).date())


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
    if body.date > now(request).astimezone(VN).date():
        return error(422, "future_date", "Ngày số liệu không được ở tương lai.")
    plain = format(value.normalize(), "f")
    store.upsert(indicator, [(body.date, plain)], entry="manual", source_url=body.source_url)
    return {"indicator": indicator, "date": body.date.isoformat(), "value": plain}
