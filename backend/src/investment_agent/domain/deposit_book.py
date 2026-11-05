"""Sổ tiền gửi: the owner's term deposits and cash accounts outside the securities account, the months their money comes back, and how much
can be withdrawn now against the protected reserve. A deposit not yet due, locked or not, is never cash now; one past its date is overdue
(rolled over or closed is unknown, so it is not guessed). Blank fields stay unknown, never 0. Personal data; never sent to a model."""

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .models import ContractModel, UnsignedAmount

DUE_SOON_DAYS, MATURING_DAYS = 30, 90


def _whole(value: Decimal | None) -> Decimal | None:
    if value is not None and value != value.to_integral_value():
        raise ValueError("amount must be whole đồng")
    return value


class CashAccount(ContractModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=60, pattern=r"\S")
    amount: UnsignedAmount
    liquid: bool

    _amount_whole = field_validator("amount")(_whole)


class Deposit(ContractModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    bank: str = Field(min_length=1, max_length=40, pattern=r"\S")
    matures: date
    principal: UnsignedAmount
    rate: Decimal | None = Field(default=None, ge=0, le=30, allow_inf_nan=False)  # percent per year as written on the sổ
    interest: UnsignedAmount | None = None  # expected at maturity as written on the sổ
    payout: Literal["end", "upfront"]  # upfront: already received when the sổ was opened
    locked: bool  # phong tỏa đến hạn: cannot be withdrawn early

    _amounts_whole = field_validator("principal", "interest")(_whole)

    @field_validator("principal")
    @classmethod
    def _positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("principal must be positive")
        return value


class DepositBook(ContractModel):
    accounts: tuple[CashAccount, ...] = Field(default=(), max_length=30)
    deposits: tuple[Deposit, ...] = Field(default=(), max_length=100)
    count_ledger_cash: bool = True  # False: the owner's cash is the accounts here only; the ledger's cash is shown, not counted

    @model_validator(mode="after")
    def _unique_ids(self):
        if any(n > 1 for n in Counter(x.id for x in (*self.accounts, *self.deposits)).values()):
            raise ValueError("row ids must be unique")
        return self


def _s(value: Decimal) -> str:
    return format(value, "f")


def maturity_calendar(book: DepositBook, *, today: date) -> dict:
    """Months from today with the count, principal and the interest that arrives at maturity (end payout with interest entered; upfront
    interest was already received). Ids due within 30 days and ids past maturity, both soonest first."""
    months: dict[str, dict] = {}
    ahead = sorted((d for d in book.deposits if d.matures >= today), key=lambda d: d.matures)
    for d in ahead:
        m = months.setdefault(d.matures.strftime("%Y-%m"), {"count": 0, "principal": Decimal(0), "interest": Decimal(0), "missing_interest": 0})
        m["count"] += 1
        m["principal"] += d.principal
        if d.payout == "end":
            if d.interest is None:
                m["missing_interest"] += 1
            else:
                m["interest"] += d.interest
    return {"months": [{"month": k, "count": v["count"], "principal": _s(v["principal"]), "interest": _s(v["interest"]),
                        "missing_interest": v["missing_interest"]} for k, v in months.items()],
            "due_soon": [d.id for d in ahead if d.matures <= today + timedelta(days=DUE_SOON_DAYS)],
            "overdue": [d.id for d in sorted(book.deposits, key=lambda d: d.matures) if d.matures < today]}


def liquidity(book: DepositBook, *, ledger_cash: Decimal, reserve: Decimal, today: date) -> dict:
    """Cash now (ledger cash unless the owner keeps cash to the book, + accounts marked liquid) against the reserve; everything else
    is named apart, and not counted."""
    def total(rows) -> Decimal:
        return sum(rows, Decimal(0))
    liquid = total(a.amount for a in book.accounts if a.liquid)
    now = (ledger_cash if book.count_ledger_cash else Decimal(0)) + liquid
    ahead = [d for d in book.deposits if d.matures >= today]
    short = reserve - now
    return {"now": _s(now), "ledger_cash": _s(ledger_cash), "ledger_cash_counted": book.count_ledger_cash, "accounts_liquid": _s(liquid),
            "not_now": {"accounts": _s(total(a.amount for a in book.accounts if not a.liquid)),
                        "locked": _s(total(d.principal for d in ahead if d.locked)),
                        "unlocked": _s(total(d.principal for d in ahead if not d.locked)),
                        "overdue": _s(total(d.principal for d in book.deposits if d.matures < today))},
            "reserve": _s(reserve), "status": "short" if short > 0 else "enough", "short": _s(short) if short > 0 else None,
            "maturing_90d": _s(total(d.principal for d in ahead if d.matures <= today + timedelta(days=MATURING_DAYS)))}


def totals(book: DepositBook) -> dict[str, Decimal]:
    """Principal of every deposit (overdue ones are still in the bank) and every cash account, for Tháp tài sản."""
    return {"deposits": sum((d.principal for d in book.deposits), Decimal(0)), "accounts": sum((a.amount for a in book.accounts), Decimal(0))}


def deposit_income(book: DepositBook, *, market_rate: Decimal) -> dict:
    """Monthly interest, unrounded: principal × the sổ's own rate / 12, or the market 12-month rate for a sổ without one (counted)."""
    monthly = sum((d.principal * (d.rate if d.rate is not None else market_rate) / 100 / 12 for d in book.deposits), Decimal(0))
    return {"monthly": monthly, "market_rate_count": sum(1 for d in book.deposits if d.rate is None)}
