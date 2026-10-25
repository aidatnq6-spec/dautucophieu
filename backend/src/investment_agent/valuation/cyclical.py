"""Cycle-normalised earnings: the mean over a stated full-cycle window, capitalised at the cost of equity.

The window and its reason are owner-approved inputs. A peak year is never
taken as sustainable, and history shorter than the window is unavailable.
"""

from decimal import Decimal

from pydantic import Field, model_validator

from investment_agent.domain.models import ContractModel, NonemptyId, Ratio, SignedAmount

from .common import ApprovalRef, SectorResult, finish, s

MIN_WINDOW_YEARS = 5


class YearEps(ContractModel):
    year: NonemptyId
    eps: SignedAmount


class CyclicalInputs(ApprovalRef):
    eps_history: tuple[YearEps, ...]
    window_years: int = Field(strict=True, ge=MIN_WINDOW_YEARS)
    reason: str = Field(min_length=1)
    cost_of_equity: Ratio

    @model_validator(mode="after")
    def _rate(self):
        if self.cost_of_equity <= 0:
            raise ValueError("cost of equity must be positive")
        return self


class CyclicalResult(SectorResult):
    normalized_eps: SignedAmount | None = None
    window: tuple[str, ...] = ()


def value_cyclical(i: CyclicalInputs) -> CyclicalResult:
    history = sorted(i.eps_history, key=lambda r: r.year)
    if len(history) < i.window_years:
        return CyclicalResult(**finish("cyclical_normalized", i, None, None, reason="history_shorter_than_window"))
    window = history[-i.window_years:]
    eps = sum((r.eps for r in window), Decimal(0)) / i.window_years
    if eps <= 0:
        return CyclicalResult(**finish("cyclical_normalized", i, None, None, reason="non_positive_normalized_eps"))
    # Per-share model: equity_value is per share, shares = 1.
    return CyclicalResult(**finish("cyclical_normalized", i, eps / i.cost_of_equity, 1), normalized_eps=s(eps),
                          window=tuple(r.year for r in window))
