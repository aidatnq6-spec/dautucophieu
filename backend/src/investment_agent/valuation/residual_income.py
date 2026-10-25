"""Residual income for banks: value = book equity + PV of (ROE − ke) × opening book.

Book grows by retained earnings each year. With ROE equal to the cost of
equity, residual income is zero and value equals book: no premium appears by
itself. Projected capital ratios below the regulatory minimum flag the result
and keep its buy zone inactive, since that ROE path would need fresh capital.
"""

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from investment_agent.domain.models import Ratio, UnsignedAmount

from .common import ApprovalRef, SectorResult, finish


class ResidualIncomeInputs(ApprovalRef):
    book_equity: UnsignedAmount
    roe_path: tuple[Ratio, ...] = Field(min_length=1)
    payout_path: tuple[Ratio, ...]
    cost_of_equity: Ratio
    terminal: Literal["fade_to_zero", "perpetuity"]
    terminal_growth: Ratio
    capital_ratio_path: tuple[Ratio, ...]
    regulatory_minimum: Ratio
    shares: int | None = Field(default=None, strict=True, gt=0)

    @model_validator(mode="after")
    def _paths(self):
        if not len(self.roe_path) == len(self.payout_path) == len(self.capital_ratio_path):
            raise ValueError("ROE, payout and capital paths need one value per year")
        if self.cost_of_equity <= 0 or (self.terminal == "perpetuity" and self.terminal_growth >= self.cost_of_equity):
            raise ValueError("cost of equity must be positive and above terminal growth")
        return self


def value_residual_income(i: ResidualIncomeInputs) -> SectorResult:
    book, factor, pv, last_ri = i.book_equity, Decimal(1), Decimal(0), Decimal(0)
    for roe, payout in zip(i.roe_path, i.payout_path):
        factor *= 1 + i.cost_of_equity
        last_ri = (roe - i.cost_of_equity) * book
        pv += last_ri / factor
        book += roe * book * (1 - payout)
    if i.terminal == "perpetuity":
        pv += last_ri * (1 + i.terminal_growth) / (i.cost_of_equity - i.terminal_growth) / factor
    flags = ["capital_below_regulatory_minimum"] if any(c < i.regulatory_minimum for c in i.capital_ratio_path) else []
    return SectorResult(**finish("residual_income", i, i.book_equity + pv, i.shares, flags=flags,
                                 reason=None if i.shares else "shares_missing"))
