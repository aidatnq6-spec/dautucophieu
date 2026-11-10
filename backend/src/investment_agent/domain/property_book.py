"""Bất động sản và khoản vay: what the owner enters row by row, and the whole picture with their financial assets. Values are the owner's own
estimates; a blank is unknown, never 0, and a total that would rest on one is not given. Kept apart from Tháp tài sản, which decides the money for
stocks. Personal data; never sent to a model."""

import calendar
from collections import Counter
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .deposit_book import _whole
from .models import ContractModel, UnsignedAmount

STALE_DAYS = 180
_ID = r"^[A-Za-z0-9_-]{1,64}$"
_Q4 = Decimal("0.0001")


class Property(ContractModel):
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1, max_length=80, pattern=r"\S")
    kind: Literal["home", "apartment", "land", "other"]
    purpose: Literal["live", "rent", "invest"]
    value: UnsignedAmount | None = None
    valued_on: date | None = None
    legal: Literal["certificate", "contract", "unknown"]
    cost: UnsignedAmount | None = None
    bought_year: int | None = Field(default=None, ge=1900, le=2100)
    rent_monthly: UnsignedAmount | None = None

    _whole_amounts = field_validator("value", "cost", "rent_monthly")(_whole)


class Loan(ContractModel):
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1, max_length=80, pattern=r"\S")
    bank: str | None = Field(default=None, max_length=40)
    balance: UnsignedAmount | None = None
    balance_on: date | None = None
    rate: Decimal | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)  # percent per year, now
    promo_ends: date | None = None
    after_rate: Decimal | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    months_left: int | None = Field(default=None, ge=1, le=600)
    method: Literal["declining", "annuity"]
    collateral: str | None = Field(default=None, pattern=_ID)  # a Property id

    _whole_balance = field_validator("balance")(_whole)


FREQ_MONTHS = {"year": 12, "half": 6, "quarter": 3, "month": 1}


class Policy(ContractModel):
    """An insurance policy. Only life cover holds a value: the account value as the insurer reports it (before the surrender charge) and, when
    known, the surrender value, which is what cashing it in would pay. due_on: any one date a premium is due; the next is worked out."""
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1, max_length=80, pattern=r"\S")
    insurer: str | None = Field(default=None, max_length=40)
    insured: str | None = Field(default=None, max_length=40)
    kind: Literal["life", "property", "health", "other"]
    premium: UnsignedAmount | None = None
    frequency: Literal["year", "half", "quarter", "month"]
    due_on: date | None = None
    matures: date | None = None
    sum_assured: UnsignedAmount | None = None
    account_value: UnsignedAmount | None = None
    surrender_value: UnsignedAmount | None = None
    valued_on: date | None = None

    _whole_amounts = field_validator("premium", "sum_assured", "account_value", "surrender_value")(_whole)

    @model_validator(mode="after")
    def _value_only_for_life(self):
        if self.kind != "life" and (self.account_value is not None or self.surrender_value is not None):
            raise ValueError("only life cover holds a value")
        return self


class PropertyBook(ContractModel):
    properties: tuple[Property, ...] = Field(default=(), max_length=30)
    loans: tuple[Loan, ...] = Field(default=(), max_length=30)
    policies: tuple[Policy, ...] = Field(default=(), max_length=30)
    ceiling: Decimal = Field(default=Decimal(70), gt=0, le=100, allow_inf_nan=False)  # percent of all assets; the owner's own warning line

    @model_validator(mode="after")
    def _consistent(self):
        if any(n > 1 for n in Counter(x.id for x in (*self.properties, *self.loans, *self.policies)).values()):
            raise ValueError("row ids must be unique")
        known = {p.id for p in self.properties}
        if any(x.collateral is not None and x.collateral not in known for x in self.loans):
            raise ValueError("a loan's collateral must be a property in the book")
        return self


def _s(value: Decimal) -> str:
    return format(value, "f")


def _ratio(a: Decimal, b: Decimal) -> str | None:
    return _s((a / b).quantize(_Q4, ROUND_HALF_UP)) if b else None


def loan_payment(loan: Loan) -> Decimal | None:
    """This month's payment at the current rate, to the đồng; None without the balance, the rate or the months left."""
    if loan.balance is None or loan.rate is None or loan.months_left is None:
        return None
    monthly, n = loan.rate / 100 / 12, loan.months_left
    if loan.method == "declining":
        payment = loan.balance / n + loan.balance * monthly
    elif monthly == 0:
        payment = loan.balance / n
    else:
        payment = loan.balance * monthly / (1 - (1 + monthly) ** -n)
    return payment.quantize(Decimal(1), ROUND_HALF_UP)


def rent_now(book: PropertyBook) -> tuple[Decimal, list[str]]:
    """Monthly rent entered, and the properties let out with none entered: those are named, never taken as 0."""
    return (sum((p.rent_monthly for p in book.properties if p.rent_monthly is not None), Decimal(0)),
            [p.name for p in book.properties if p.purpose == "rent" and p.rent_monthly is None])


def _add_months(day: date, months: int) -> date:
    y, m = divmod(day.month - 1 + months, 12)
    year, month = day.year + y, m + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def next_due(policy: Policy, today: date) -> date | None:
    """The first premium date on or after today, counted from due_on in steps of the period; None without a date or once the policy has ended."""
    if policy.due_on is None:
        return None
    step = FREQ_MONTHS[policy.frequency]
    k = ((today.year - policy.due_on.year) * 12 + today.month - policy.due_on.month) // step - 1
    while _add_months(policy.due_on, k * step) < today:
        k += 1
    while _add_months(policy.due_on, (k - 1) * step) >= today:
        k -= 1
    due = _add_months(policy.due_on, k * step)
    return None if policy.matures is not None and due > policy.matures else due


def picture(book: PropertyBook, *, financial: Decimal | None, today: date) -> dict:
    """financial: Tháp tài sản's layers with stocks at market price, None when not known. Totals and shares are given only when every value and
    balance is there (complete); what is missing is named."""
    valued = [p for p in book.properties if p.value is not None]
    property_total = sum((p.value for p in valued), Decimal(0))
    unclear = sum((p.value for p in valued if p.legal == "unknown"), Decimal(0))
    debt = sum((x.balance for x in book.loans if x.balance is not None), Decimal(0))
    payments = {x.id: loan_payment(x) for x in book.loans}
    rent = sum((p.rent_monthly for p in book.properties if p.rent_monthly is not None), Decimal(0))
    paid = sum((v for v in payments.values() if v is not None), Decimal(0))
    property_missing = [p.name for p in book.properties if p.value is None]
    debt_missing = [x.name for x in book.loans if x.balance is None]
    payments_missing = [x.name for x in book.loans if payments[x.id] is None]
    limit = today - timedelta(days=STALE_DAYS)
    life = [p for p in book.policies if p.kind == "life"]
    held = {p.id: p.surrender_value if p.surrender_value is not None else p.account_value for p in life}
    insurance = sum((v for v in held.values() if v is not None), Decimal(0))
    insurance_missing = [p.name for p in life if held[p.id] is None]
    yearly = sum((p.premium * 12 / FREQ_MONTHS[p.frequency] for p in book.policies if p.premium is not None), Decimal(0))
    complete = financial is not None and not property_missing and not debt_missing and not insurance_missing
    out = {"financial": _s(financial) if financial is not None else None, "property_total": _s(property_total), "property_missing": property_missing,
           "stale": [p.name for p in book.properties if p.valued_on is None or p.valued_on < limit], "debt": _s(debt), "debt_missing": debt_missing,
           "payments": _s(paid), "payments_missing": payments_missing, "rent": _s(rent), "rent_less_payments": _s(rent - paid) if not payments_missing else None,
           "loans": {k: (_s(v) if v is not None else None) for k, v in payments.items()}, "ceiling": _s(book.ceiling), "complete": complete,
           "insurance": _s(insurance), "insurance_missing": insurance_missing,
           "insurance_at_account": [p.name for p in life if p.surrender_value is None and p.account_value is not None],
           "insurance_stale": [p.name for p in life if held[p.id] is not None and (p.valued_on is None or p.valued_on < limit)],
           "premiums_yearly": _s(yearly.quantize(Decimal(1), ROUND_HALF_UP)), "premiums_missing": [p.name for p in book.policies if p.premium is None],
           "policy_due": {p.id: (d.isoformat() if (d := next_due(p, today)) else None) for p in book.policies},
           "insurance_share": None, "insurance_of_invest": None,
           "yields": {p.id: _ratio(p.rent_monthly * 12, p.value) if p.rent_monthly is not None and p.value else None for p in book.properties},
           "live_total": None, "invest_total": None, "invest_property_total": None, "live_share": None, "invest_share": None, "invest_property_of_invest": None, "financial_of_invest": None,
           "total_assets": None, "net_worth": None, "liquid_share": None, "clear_share": None, "unclear_share": None, "property_share": None, "debt_ratio": None, "over": False}
    if complete:
        total = financial + property_total + insurance
        live = sum((p.value for p in valued if p.purpose == "live"), Decimal(0))
        invest = total - live
        out |= {"live_total": _s(live), "invest_total": _s(invest), "invest_property_total": _s(property_total - live), "live_share": _ratio(live, total), "invest_share": _ratio(invest, total),
                "invest_property_of_invest": _ratio(property_total - live, invest), "financial_of_invest": _ratio(financial, invest),
                "insurance_share": _ratio(insurance, total), "insurance_of_invest": _ratio(insurance, invest)}
        out |= {"total_assets": _s(total), "net_worth": _s(total - debt), "liquid_share": _ratio(financial, total), "clear_share": _ratio(property_total - unclear, total),
                "unclear_share": _ratio(unclear, total), "property_share": _ratio(property_total, total), "debt_ratio": _ratio(debt, total),
                "over": bool(total) and property_total / total * 100 > book.ceiling}
    return out
