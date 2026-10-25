"""P/E (TTM) and P/B from point-in-time facts on a share basis consistent with raw prices.

EPS TTM sums four contiguous fiscal quarters of parent net income from one
statement scope (consolidated preferred), never an annual figure. The share
basis is the period-end share count of the latest quarter used, scaled by
split and stock-dividend actions with ex-date after that period end and on or
before the valuation date. Non-positive EPS or equity makes the ratio
unavailable rather than "cheap".
"""

from datetime import date
from decimal import Decimal

from investment_agent.domain.models import ContractModel

from .financials import FinancialFact
from .prices import AdjustmentFactor


class RatioResult(ContractModel):
    value: Decimal | None
    reason: str | None = None
    method_version: str
    provenance_mode: str | None = None
    share_basis: Decimal | None = None
    inputs: tuple[str, ...] = ()
    inputs_period_labels: tuple[str, ...] = ()
    derived_inputs: bool = False


def _mode(facts: list[FinancialFact]) -> str | None:
    modes = {f.provenance_mode for f in facts}
    if len(modes) > 1:
        raise ValueError("provenance modes must not be mixed")
    return modes.pop() if modes else None


def _quarter(f: FinancialFact) -> int:
    return f.period_end.year * 4 + (f.period_end.month - 1) // 3


def _ttm_quarters(facts, entity_id):
    for scope in ("consolidated", "separate"):
        rows = sorted((f for f in facts if f.entity_id == entity_id and f.metric == "net_income_parent"
                       and f.period_type == "quarter" and f.statement_scope == scope), key=_quarter)
        if not rows:
            continue
        last = rows[-4:]
        if len(last) == 4 and [_quarter(r) for r in last] == list(range(_quarter(last[0]), _quarter(last[0]) + 4)):
            return scope, last
        return scope, None  # the preferred scope exists but is incomplete: never fill from another scope
    return None, None


def _share_basis(facts, entity_id, scope, period_end, valuation_date, share_actions):
    shares = [f for f in facts if f.entity_id == entity_id and f.metric == "shares_outstanding" and f.period_end == period_end
              and f.statement_scope == scope]
    if not shares or shares[0].value <= 0:
        return None, ()
    basis, used = shares[0].value, [shares[0].revision_id]
    for a in share_actions:
        if a.entity_id == entity_id and a.kind in {"split", "stock_dividend"} and period_end < a.ex_date <= valuation_date:
            basis /= a.factor
            used.append(a.action_id)
    return basis, tuple(used)


def ttm_eps(facts: list[FinancialFact], entity_id: str, *, share_actions: list[AdjustmentFactor] = (),
            valuation_date: date | None = None) -> RatioResult:
    mode = _mode(facts)
    scope, quarters = _ttm_quarters(facts, entity_id)
    if quarters is None:
        return RatioResult(value=None, reason="quarters_missing", method_version="eps_ttm_v1", provenance_mode=mode)
    end = quarters[-1].period_end
    basis, used = _share_basis(facts, entity_id, scope, end, valuation_date or end, share_actions)
    if basis is None:
        return RatioResult(value=None, reason="shares_missing", method_version="eps_ttm_v1", provenance_mode=mode)
    income = sum((q.value for q in quarters), Decimal(0))
    return RatioResult(value=income / basis, method_version="eps_ttm_v1", provenance_mode=mode, share_basis=basis,
                       inputs=tuple(f"{q.revision_id}:{q.fiscal_label}" for q in quarters) + used,
                       inputs_period_labels=tuple(q.fiscal_label for q in quarters), derived_inputs=any(q.derived for q in quarters))


def price_to_earnings(price: Decimal, facts, entity_id, *, valuation_date: date, share_actions) -> RatioResult:
    eps = ttm_eps(facts, entity_id, share_actions=share_actions, valuation_date=valuation_date)
    if eps.value is None:
        return eps.model_copy(update={"method_version": "pe_ttm_v1"})
    if eps.value <= 0:
        return eps.model_copy(update={"value": None, "reason": "non_positive_eps", "method_version": "pe_ttm_v1"})
    return eps.model_copy(update={"value": price / eps.value, "method_version": "pe_ttm_v1"})


def price_to_book(price: Decimal, facts, entity_id, *, valuation_date: date, share_actions) -> RatioResult:
    mode = _mode(facts)
    equity = [f for f in facts if f.entity_id == entity_id and f.metric == "equity_parent" and f.period_type == "quarter"]
    if not equity:
        return RatioResult(value=None, reason="equity_missing", method_version="pb_v1", provenance_mode=mode)
    latest = max(equity, key=lambda f: (f.period_end, f.statement_scope == "consolidated"))
    if latest.value <= 0:
        return RatioResult(value=None, reason="non_positive_equity", method_version="pb_v1", provenance_mode=mode)
    basis, used = _share_basis(facts, entity_id, latest.statement_scope, latest.period_end, valuation_date, share_actions)
    if basis is None:
        return RatioResult(value=None, reason="shares_missing", method_version="pb_v1", provenance_mode=mode)
    return RatioResult(value=price / (latest.value / basis), method_version="pb_v1", provenance_mode=mode, share_basis=basis,
                       inputs=(f"{latest.revision_id}:{latest.fiscal_label}", *used), inputs_period_labels=(latest.fiscal_label,))
