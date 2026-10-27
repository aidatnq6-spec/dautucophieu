"""Leading macro indicators: automatic values from free feeds plus the owner's entries."""

from datetime import date
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.rate_cycle import US, VIETNAM, rate_cycle
from investment_agent.market.leading import MacroStore, load_indicators, macro_rows

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
