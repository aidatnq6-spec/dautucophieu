"""Kế hoạch tích sản: a fixed monthly purchase of gold (in chỉ) or a fund (in đồng), each purchase recorded, the months met and the average cost. It counts and reminds;
it never says what to buy, and a purchase recorded here does not change Sổ tài sản or Tháp tài sản. Personal data; never sent to a model."""

from collections import Counter
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .contributions import _months
from .deposit_book import GOLD_STALE_DAYS, MAX_HOLDING_ROWS, NAV_STALE_DAYS, DepositBook, _whole
from .models import ContractModel, UnsignedAmount

_ID = r"^[A-Za-z0-9_-]{1,64}$"
_Quantity = Field(gt=0, max_digits=16, decimal_places=4, allow_inf_nan=False)


class Plan(ContractModel):
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1, max_length=60, pattern=r"\S")
    asset: Literal["gold", "fund"]
    day: int = Field(ge=1, le=28)
    start: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    chi: Decimal | None = Field(default=None, gt=0, max_digits=16, decimal_places=4, allow_inf_nan=False)  # gold: chỉ a month
    amount: UnsignedAmount | None = None  # fund: đồng a month
    kind: str | None = Field(default=None, min_length=1, max_length=80)  # gold: the kind in the public price table
    fund: str | None = Field(default=None, pattern=r"^[A-Z0-9][A-Z0-9-]{1,15}$")

    _whole_amount = field_validator("amount")(_whole)

    @model_validator(mode="after")
    def _one_measure(self):
        fits = self.chi is not None and self.amount is None and self.fund is None if self.asset == "gold" else self.amount is not None and self.amount > 0 and self.chi is None and self.kind is None
        if not fits:
            raise ValueError("gold is planned in chỉ, a fund in đồng")
        return self


class Buy(ContractModel):
    id: str = Field(pattern=_ID)
    plan: str = Field(pattern=_ID)
    on: date
    amount: UnsignedAmount  # what was paid
    quantity: Decimal = _Quantity  # chỉ or fund units
    book_row: str | None = Field(default=None, pattern=_ID)  # the row of Sổ tài sản it was added to, once the owner has done so

    _whole_amount = field_validator("amount")(_whole)


class Accumulation(ContractModel):
    plans: tuple[Plan, ...] = Field(default=(), max_length=20)
    buys: tuple[Buy, ...] = Field(default=(), max_length=3000)

    @model_validator(mode="after")
    def _consistent(self):
        known = {p.id for p in self.plans}
        if any(n > 1 for n in Counter(x.id for x in (*self.plans, *self.buys)).values()):
            raise ValueError("ids must be unique")
        if any(b.plan not in known for b in self.buys):
            raise ValueError("a purchase must belong to a plan")
        return self


def _n(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def _vnd(value: Decimal) -> str:
    return format(value.quantize(Decimal(1), ROUND_HALF_UP), "f")


def _quote(plan: Plan, quotes: dict) -> tuple[dict | None, str | None]:
    """({price, on, stale days limit}, reason when there is none). Never a guessed price."""
    if plan.asset == "gold":
        if plan.kind is None:
            return None, "no_kind"
        gold = quotes.get("gold") or {}
        row = (gold.get("kinds") or {}).get(plan.kind)
        return ({"price": row["buy"], "on": gold["as_of"][:10], "limit": GOLD_STALE_DAYS}, None) if row else (None, "no_price")
    if plan.fund is None:
        return None, "no_kind"
    row = (quotes.get("funds") or {}).get(plan.fund)
    return ({"price": row["nav"], "on": row["date"], "limit": NAV_STALE_DAYS}, None) if row else (None, "no_price")


def plan_status(plan: Plan, buys: tuple[Buy, ...], quotes: dict, *, today: date) -> dict:
    """Each month from the start: met, short, none, or pending (the current month before its day and not yet met). Average cost over the purchases recorded."""
    mine = [b for b in buys if b.plan == plan.id]
    target = plan.chi if plan.asset == "gold" else plan.amount
    got: dict[str, Decimal] = {}
    for b in mine:
        key = b.on.strftime("%Y-%m")
        got[key] = got.get(key, Decimal(0)) + (b.quantity if plan.asset == "gold" else b.amount)
    now, months = today.strftime("%Y-%m"), []
    for key in _months(plan.start, today):
        have = got.get(key, Decimal(0))
        status = "met" if have >= target else "pending" if key == now and today.day < plan.day else "short" if have > 0 else "none"
        months.append({"month": key, "got": _n(have), "status": status, "short_by": _n(target - have) if status == "short" else None})
    streak = 0
    for m in reversed([m for m in months if m["status"] != "pending"]):
        if m["status"] != "met":
            break
        streak += 1
    cost, quantity = sum((b.amount for b in mine), Decimal(0)), sum((b.quantity for b in mine), Decimal(0))
    out = {"id": plan.id, "months": months, "streak": streak, "cost": _n(cost), "quantity": _n(quantity), "average": _vnd(cost / quantity) if quantity else None,
           "before_start": sum(1 for b in mine if b.on.strftime("%Y-%m") < plan.start), "price": None, "price_on": None, "stale": False, "value": None, "change": None, "price_reason": "no_buys"}
    if quantity:
        quote, reason = _quote(plan, quotes)
        out["price_reason"] = reason
        if quote:
            value = (quantity * Decimal(quote["price"])).quantize(Decimal(1), ROUND_HALF_UP)
            out |= {"price": quote["price"], "price_on": quote["on"], "stale": (today - date.fromisoformat(quote["on"])).days > quote["limit"], "value": _s(value), "change": _s(value - cost)}
    return out


def _s(value: Decimal) -> str:
    return format(value, "f")


class PostRefused(ValueError):
    """Why this purchase cannot go into Sổ tài sản, in the owner's language."""


def book_targets(book: DepositBook, plan: Plan) -> list[dict]:
    """The rows of the book that can take this plan's purchases: priced the same way, so what is added is valued as it was bought."""
    if plan.asset == "gold":
        return [{"id": r.id, "name": r.name} for r in book.gold if r.kind == plan.kind]
    return [{"id": r.id, "name": r.name} for r in book.bonds if r.fund == plan.fund]


def post_to_book(book: DepositBook, plan: Plan, buy: Buy, row_id: str | None, *, new_id: str) -> tuple[DepositBook, str]:
    """The book with this purchase added: money to what the row cost and, for a row that counts them, chỉ or units to its quantity. row_id None: a new row named after the plan."""
    gold = plan.asset == "gold"
    field, list_name, code_field, code = ("chi", "gold", "kind", plan.kind) if gold else ("units", "bonds", "fund", plan.fund)
    data = book.model_dump(mode="json")
    rows = list(data[list_name])
    def checked() -> None:
        if buy.quantity != buy.quantity.quantize(Decimal("0.01")):
            raise PostRefused("Sổ tài sản chỉ nhận số lượng tối đa 2 chữ số thập phân; lần mua này có nhiều hơn.")
    if row_id is None:
        if len(rows) >= MAX_HOLDING_ROWS:
            raise PostRefused("Danh sách này trong Sổ tài sản đã đầy; hãy chọn một dòng có sẵn.")
        if code is not None:
            checked()
        rows.append({"id": new_id, "name": plan.name, "amount": _s(buy.amount), code_field: code, field: _s(buy.quantity) if code is not None else None, **({} if gold else {"rate": None})})
        row_id = new_id
    else:
        if row_id not in {r["id"] for r in book_targets(book, plan)}:
            raise PostRefused("Dòng này không dùng được: cần cùng loại giá vàng hoặc cùng mã quỹ với kế hoạch.")
        for i, row in enumerate(rows):
            if row["id"] == row_id:
                if row[field] is not None:
                    checked()
                rows[i] = {**row, "amount": _s(Decimal(row["amount"]) + buy.amount), field: _s(Decimal(row[field]) + buy.quantity) if row[field] is not None else None}
    return DepositBook.model_validate({**data, list_name: rows}), row_id


def due_plans(data: Accumulation, quotes: dict, *, today: date) -> list[tuple[Plan, dict]]:
    """Plans whose current month is past its day and not yet met, with this month's line."""
    out = []
    for plan in data.plans:
        months = plan_status(plan, data.buys, quotes, today=today)["months"]
        if months and months[-1]["month"] == today.strftime("%Y-%m") and months[-1]["status"] in ("short", "none"):
            out.append((plan, months[-1]))
    return out
