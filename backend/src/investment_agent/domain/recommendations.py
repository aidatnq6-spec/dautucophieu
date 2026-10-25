"""Constraint-checked proposals. A recommendation never becomes a ledger event.

Order of gates: research scope → basis (approved valuation, price, analysis
gaps, profile, risk, capital) → price zone → financial capacity → buying power
→ post-trade allocation. A buy amount is the smallest of one tranche of the
long-term target, the allocation headroom, and buying power net of the
owner's fee rate. Lot rules are unverified, so only an amount is proposed and
the quantity must be confirmed by the owner. A low P/B is informational and
never relaxes any gate.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from investment_agent.domain.models import ContractModel, NonemptyId, PlainDecimal, Ratio, SignedAmount
from investment_agent.valuation.price_zones import Zone, compute_zone

from .allocation import Position, evaluate_allocation, load_allocation_policy
from .investable_capital import CapitalAssessment
from .profile import ProfileFreshness
from .risk import RiskAssessment


class ValuationSummary(ContractModel):
    entity_id: NonemptyId
    status: Literal["approved", "draft", "unavailable"]
    buy_zone_active: bool
    assumption_version: int | None
    per_share: dict[Literal["down", "base", "up"], SignedAmount | None]
    required_margin: Ratio | None
    tranche_fraction: Ratio | None
    source_ids: tuple[NonemptyId, ...]


@dataclass(frozen=True)
class RecommendationInputs:
    entity_id: str
    industry: str | None
    control_group_id: str | None
    scope: Literal["research", "held_outside_universe", "removed_stop_buy"]
    valuation: ValuationSummary
    price: Decimal | None
    price_date: date | None
    pb: Decimal | None  # shown for context only
    analysis_gaps: tuple[str, ...]
    governance_status: str
    capital: CapitalAssessment
    risk: RiskAssessment
    freshness: ProfileFreshness
    holdings: list[Position]
    held_quantity: int
    buying_power: Decimal | None
    buying_power_basis: str
    fee_rate: Decimal
    now: datetime
    history_window: tuple[date, date] | None = None
    policy: object = field(default=None)


class Recommendation(ContractModel):
    entity_id: str
    action: Literal["buy_tranche", "hold", "reduce", "wait", "insufficient_basis"]
    reasons: tuple[str, ...]
    zone: Zone | None
    amount: PlainDecimal
    shares: int | None
    quantity_requires_confirmation: bool
    weight_before: PlainDecimal | None
    weight_after: PlainDecimal | None
    constraints: tuple[str, ...]
    source_ids: tuple[str, ...]
    assumption_version: int | None
    invalidate_conditions: tuple[str, ...]
    price_date: date | None
    analysis_time: datetime
    history_window: tuple[date, date] | None
    pb_context: PlainDecimal | None


def _result(i: RecommendationInputs, action, reasons, *, zone=None, amount=Decimal(0), before=None, after=None, constraints=(), conditions=()):
    return Recommendation(entity_id=i.entity_id, action=action, reasons=tuple(reasons), zone=zone, amount=amount, shares=None,
                          quantity_requires_confirmation=action == "buy_tranche", weight_before=before, weight_after=after,
                          constraints=tuple(constraints), source_ids=i.valuation.source_ids, assumption_version=i.valuation.assumption_version,
                          invalidate_conditions=tuple(conditions), price_date=i.price_date, analysis_time=i.now,
                          history_window=i.history_window, pb_context=i.pb)


def recommend(i: RecommendationInputs) -> Recommendation:
    policy = i.policy or load_allocation_policy()
    held = i.held_quantity > 0
    if i.scope != "research":
        reason = "outside_research_universe" if i.scope == "held_outside_universe" else "removed_from_universe"
        return _result(i, "hold" if held else "wait", [reason])

    v = i.valuation
    gaps = []
    if v.status == "unavailable" or any(v.per_share.get(k) is None for k in ("down", "base", "up")):
        gaps.append("valuation_unavailable")
    elif v.status != "approved" or not v.buy_zone_active:
        gaps.append("assumptions_not_approved")
    if v.required_margin is None or v.tranche_fraction is None:
        gaps.append("zone_policy_missing")
    if i.price is None:
        gaps.append("price_missing")
    if i.analysis_gaps:
        gaps.append("analysis_gaps")
    if not i.freshness.allows_new_recommendations:
        gaps.append("profile_reconfirm_required")
    if not i.risk.ready_for_allocation:
        gaps.append("risk_needs_confirmation")
    if i.capital.status != "ready":
        gaps.append("capital_not_ready")
    if gaps:
        return _result(i, "insufficient_basis", gaps)

    zone = compute_zone(base=v.per_share["base"], down=v.per_share["down"], up=v.per_share["up"], price=i.price,
                        required_margin=v.required_margin)
    if held and zone.position == "above_up_scenario":
        return _result(i, "reduce", ["price_above_up_scenario"], zone=zone)
    if zone.position != "below_buy_zone":
        return _result(i, "hold" if held else "wait", ["price_above_buy_zone"], zone=zone)
    if i.risk.blocks_capital_increase:
        return _result(i, "wait", ["capacity_blocks_increase"], zone=zone)
    if i.buying_power is None:
        return _result(i, "wait", ["buying_power_unknown"], zone=zone)

    base = evaluate_allocation(policy, capital=i.capital, risk=i.risk, freshness=i.freshness, holdings=i.holdings, buys=[], now=i.now)
    total = i.capital.investable_capital
    before = base.current_equity_value / total
    if base.status != "ok" or base.max_new_buy <= 0:
        return _result(i, "wait", ["no_allocation_headroom", *base.violations], zone=zone, before=before)
    candidates = {"tranche": v.tranche_fraction * base.long_term_target_value, "headroom_limited": base.max_new_buy,
                  "cash_limited": i.buying_power / (1 + i.fee_rate)}
    amount = min(candidates.values())
    constraints = [name for name, limit in candidates.items() if limit == amount]
    buy = Position(issuer_id=i.entity_id, control_group_id=i.control_group_id, industry=i.industry, market_value=format(amount, "f"))
    after = evaluate_allocation(policy, capital=i.capital, risk=i.risk, freshness=i.freshness, holdings=i.holdings, buys=[buy], now=i.now)
    if after.status != "ok":
        return _result(i, "wait", ["post_trade_policy_violation", *after.violations], zone=zone, before=before)
    conditions = [f"price_above:{format(zone.buy_below.normalize(), 'f')}", f"assumptions_superseded:{v.assumption_version}", "ledger_or_profile_changed"]
    return _result(i, "buy_tranche", ["below_buy_zone"], zone=zone, amount=amount, before=before,
                   after=(base.current_equity_value + amount) / total, constraints=constraints, conditions=conditions)
