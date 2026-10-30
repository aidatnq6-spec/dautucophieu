"""Tài sản vô hình on Hồ sơ & rủi ro: a log of money put into oneself (`settings/intangibles`), against a share of yearly
income from Sức khỏe tài chính. A line can be edited or deleted; earlier versions stay in the record's version history."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.intangibles import intangibles_year
from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal/intangibles")
RECORD = ("settings", "intangibles")
DEFAULT_RATE = "10"
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class EntryFields(ContractModel):
    on: date
    kind: Literal["course", "certificate", "book", "other"]
    title: str = Field(min_length=1, max_length=200)
    amount: str = Field(max_length=24)
    skill: str = Field(default="", max_length=300)


class EntryRequest(EntryFields):
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")  # also the new line's id


class EditRequest(EntryFields):
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class DeleteRequest(ContractModel):
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class TargetRequest(ContractModel):
    target_rate: str = Field(max_length=8)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _payload(record) -> dict:
    return dict(record.payload) if record else {"target_rate": DEFAULT_RATE, "entries": []}


def _view(request: Request, repo, owner) -> dict:
    record = read_version(repo, owner, *RECORD, None)
    data = _payload(record)
    wc = read_version(repo, owner, "settings", "wealth_check", None)
    income = Decimal(wc.payload["income"]) if wc else None
    year = intangibles_year(data["entries"], monthly_income=income, target_rate=Decimal(data["target_rate"]), today=now(request).astimezone(VN).date())
    entries = sorted(data["entries"], key=lambda e: (e["on"], e["id"]), reverse=True)
    return {"version": record.version if record else 0, "target_rate": data["target_rate"], "entries": entries, "year": year}


@router.get("")
def get_intangibles(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


def _write(request: Request, repo, owner, change, request_id: str):
    try:
        record = read_version(repo, owner, *RECORD, None)
        data = change(_payload(record))
        if data is not None:
            repo.write(owner, *RECORD, data, expected_version=record.version if record else 0, request_id=request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)


def _entry(entry_id: str, body: EntryFields):
    """The line to store, or an error response when the amount is not a whole, non-zero number of đồng."""
    try:
        amount = Decimal(body.amount)
    except InvalidOperation:
        return error(422, "invalid_amount", "Số tiền phải là số đồng.")
    if not amount.is_finite() or amount == 0 or amount != amount.to_integral_value():
        return error(422, "invalid_amount", "Số tiền phải là số đồng khác 0 (số âm để điều chỉnh).")
    return {"id": entry_id, "on": body.on.isoformat(), "kind": body.kind, "title": body.title.strip(), "amount": format(amount, "f"),
            "skill": body.skill.strip()}


@router.post("/entries")
def add_entry(request: Request, body: EntryRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    entry = _entry(body.request_id, body)
    if not isinstance(entry, dict):
        return entry

    def append(data):
        if any(e["id"] == entry["id"] for e in data["entries"]):
            return None  # a retry: already recorded
        return {**data, "entries": [*data["entries"], entry]}
    return _write(request, repo, owner, append, body.request_id)


@router.put("/entries/{entry_id}")
def edit_entry(entry_id: str, request: Request, body: EditRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    entry = _entry(entry_id, body)
    if not isinstance(entry, dict):
        return entry
    try:
        if not any(e["id"] == entry_id for e in _payload(read_version(repo, owner, *RECORD, None))["entries"]):
            return error(404, "entry_not_found", "Không tìm thấy dòng này trong sổ.")
    except RepositoryUnavailable:
        return unavailable()

    def replace(data):
        entries = [entry if e["id"] == entry_id else e for e in data["entries"]]
        return None if entries == data["entries"] else {**data, "entries": entries}  # a retry: already saved
    return _write(request, repo, owner, replace, body.request_id)


@router.post("/entries/{entry_id}/delete")
def delete_entry(entry_id: str, request: Request, body: DeleteRequest):
    """Deleting a line that is already gone (a retried request) changes nothing."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()

    def remove(data):
        entries = [e for e in data["entries"] if e["id"] != entry_id]
        return None if len(entries) == len(data["entries"]) else {**data, "entries": entries}
    return _write(request, repo, owner, remove, body.request_id)


@router.put("/target")
def set_target(request: Request, body: TargetRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        rate = Decimal(body.target_rate)
    except InvalidOperation:
        return error(422, "invalid_rate", "Tỷ lệ mục tiêu phải là số.")
    if not rate.is_finite() or not Decimal("0.5") <= rate <= Decimal(50):
        return error(422, "invalid_rate", "Tỷ lệ mục tiêu từ 0,5% đến 50% thu nhập năm.")
    return _write(request, repo, owner, lambda data: {**data, "target_rate": format(rate.normalize(), "f")}, body.request_id)
