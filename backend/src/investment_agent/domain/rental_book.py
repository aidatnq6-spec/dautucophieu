"""Sổ cho thuê căn hộ: each room, its tenant and lease, and every payment received; which months are paid, short or unpaid, what is owed, and
reminders for rent past its day and a lease ending within 30 days. Months are counted from the current lease's start, and never before the month the
book began tracking the room (track_from): rent received earlier sits in the owner's spreadsheet, so an unrecorded month is not an unpaid one.
Personal data; never sent to a model."""

import calendar
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from .deposit_book import _whole
from .models import ContractModel, UnsignedAmount

_ID = r"^[A-Za-z0-9_-]{1,64}$"
LEASE_AHEAD = timedelta(days=30)
MAX_MONTHS = 24


class Unit(ContractModel):
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1, max_length=20, pattern=r"\S")
    tenant: str | None = Field(default=None, max_length=80)  # blank: the room is empty
    contact: str | None = Field(default=None, max_length=80)
    rent: UnsignedAmount | None = None
    due_day: int | None = Field(default=None, ge=1, le=31)
    start: date | None = None
    ends: date | None = None
    deposit: UnsignedAmount | None = None
    broker: str | None = Field(default=None, max_length=80)
    commission: UnsignedAmount | None = None
    note: str | None = Field(default=None, max_length=160)
    track_from: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # the first month whose rent is recorded here

    _whole_amounts = field_validator("rent", "deposit", "commission")(_whole)


class Payment(ContractModel):
    id: str = Field(pattern=_ID)
    unit: str = Field(pattern=_ID)
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # the month the rent is for
    amount: UnsignedAmount
    paid_on: date
    note: str | None = Field(default=None, max_length=120)

    _whole_amount = field_validator("amount")(_whole)

    @field_validator("amount")
    @classmethod
    def _positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("a payment is more than 0")
        return v


class RentalBook(ContractModel):
    units: tuple[Unit, ...] = Field(default=(), max_length=30)
    payments: tuple[Payment, ...] = Field(default=(), max_length=5000)

    @model_validator(mode="after")
    def _consistent(self):
        if any(n > 1 for n in Counter(x.id for x in (*self.units, *self.payments)).values()):
            raise ValueError("ids must be unique")
        if any(n > 1 for n in Counter(u.name.strip().casefold() for u in self.units).values()):
            raise ValueError("room names must be unique")
        known = {u.id for u in self.units}
        if any(p.unit not in known for p in self.payments):
            raise ValueError("a payment must belong to a room")
        return self


def _s(v: Decimal) -> str:
    return format(v, "f")


def _key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def due_on(unit: Unit, month: str) -> date:
    y, m = int(month[:4]), int(month[5:])
    return date(y, m, min(unit.due_day or 1, calendar.monthrange(y, m)[1]))


def _months(unit: Unit, today: date) -> list[str]:
    first = unit.start or today.replace(day=1)
    if unit.track_from:
        first = max(first, date(int(unit.track_from[:4]), int(unit.track_from[5:]), 1))
    last = min(today, unit.ends) if unit.ends else today
    keys, y, m = [], first.year, first.month
    while (y, m) <= (last.year, last.month):
        keys.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return keys[-MAX_MONTHS:]


def unit_months(unit: Unit, payments: tuple[Payment, ...], today: date) -> list[dict]:
    if not unit.tenant or unit.rent is None:
        return []
    got: dict[str, Decimal] = {}
    for p in payments:
        if p.unit == unit.id:
            got[p.month] = got.get(p.month, Decimal(0)) + p.amount
    rows = []
    for month in _months(unit, today):
        have, day = got.get(month, Decimal(0)), due_on(unit, month)
        status = "paid" if have >= unit.rent else "pending" if today < day else "short" if have > 0 else "unpaid"
        rows.append({"month": month, "due_on": day.isoformat(), "got": _s(have), "status": status, "owed": _s(unit.rent - have if status in ("short", "unpaid") else Decimal(0))})
    return rows


def book_view(book: RentalBook, *, today: date) -> dict:
    out, owed_all = [], Decimal(0)
    for u in book.units:
        months = unit_months(u, book.payments, today)
        owed = sum((Decimal(m["owed"]) for m in months), Decimal(0))
        owed_all += owed
        out.append({"id": u.id, "vacant": not u.tenant, "months": months, "owed": _s(owed),
                    "lease_days_left": (u.ends - today).days if u.ends and u.tenant else None})
    occupied = [u for u in book.units if u.tenant]
    return {"units": out, "totals": {
        "rent_monthly": _s(sum((u.rent for u in occupied if u.rent is not None), Decimal(0))),
        "collected_year": _s(sum((p.amount for p in book.payments if p.paid_on.year == today.year), Decimal(0))),
        "owed": _s(owed_all), "deposits": _s(sum((u.deposit for u in occupied if u.deposit is not None), Decimal(0))),
        "occupied": len(occupied), "vacant": len(book.units) - len(occupied)}}


def _vnd(v: Decimal) -> str:
    return f"{v:,.0f}".replace(",", ".") + " đ"


def due_items(book: RentalBook | None, today: date) -> list[tuple[str, str, str]]:
    """(kind, key, line): rent this month past its day and not fully paid; a lease ending within 30 days. key: what a reminder is sent once for."""
    if book is None:
        return []
    out = []
    for u in book.units:
        months = unit_months(u, book.payments, today)
        now = months[-1] if months and months[-1]["month"] == _key(today) else None
        if now and now["status"] in ("short", "unpaid"):
            d = date.fromisoformat(now["due_on"])
            out.append(("rent_due", f"{u.id}:{now['month']}", f"Phòng {u.name}: chưa thu đủ tiền thuê tháng {now['month'][5:]}/{now['month'][:4]} (hạn {d:%d/%m/%Y}), còn thiếu {_vnd(Decimal(now['owed']))}"))
    for u in book.units:
        if u.tenant and u.ends and today <= u.ends <= today + LEASE_AHEAD:
            left = (u.ends - today).days
            out.append(("lease_end", f"{u.id}:end:{u.ends.isoformat()}", f"Phòng {u.name}: hợp đồng hết hạn {u.ends:%d/%m/%Y}, " + ("hết hạn hôm nay" if left == 0 else f"còn {left} ngày")))
    return out
