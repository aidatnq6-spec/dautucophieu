from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from investment_agent.domain.allocation import Position, load_allocation_policy
from investment_agent.domain.investable_capital import FinancialProfile, assess_capital
from investment_agent.domain.profile import profile_freshness
from investment_agent.domain.recommendations import RecommendationInputs, ValuationSummary, recommend
from investment_agent.domain.risk import assess_risk, load_questionnaire
from investment_agent.valuation.price_zones import compute_zone

NOW = datetime(2026, 10, 25, 9, tzinfo=timezone.utc)
M = Decimal(1_000_000)
POLICY = load_allocation_policy()


def capital(millions=1000):
    p = FinancialProfile.model_validate({"as_of": "2026-10-25", "emergency_reserve": "0",
                                         "assets": [{"asset_id": "c", "kind": "deposit", "amount": str(millions * 1_000_000), "liquidity": "liquid"}]})
    return assess_capital(p, ledger_value=None)


def risk(letters="C" * 10 + "DDD", **overrides):  # growth: 50% baseline
    chars = list(letters)
    for k, v in overrides.items():
        chars[int(k[1:]) - 1] = v
    return assess_risk(load_questionnaire(), [{"question": i + 1, "answer": a} for i, a in enumerate(chars)])


def valuation(status="approved", base="100000", down="80000", up="120000", **changes):
    data = {"entity_id": "ent-fpt", "status": status, "buy_zone_active": status == "approved", "assumption_version": 4,
            "per_share": {"down": down, "base": base, "up": up}, "required_margin": "0.20", "tranche_fraction": "0.25",
            "source_ids": ["doc-bctc-2025", "val-v4"]}
    data.update(changes)
    return ValuationSummary.model_validate(data)


def inputs(**changes):
    data = dict(entity_id="ent-fpt", industry="tech", control_group_id="ent-fpt", scope="research", valuation=valuation(),
                price=Decimal(70_000), price_date=date(2026, 10, 23), pb=None, analysis_gaps=(), governance_status="no_records_found_in_sources_checked",
                capital=capital(), risk=risk(), freshness=profile_freshness(NOW - timedelta(days=2), NOW), holdings=[],
                held_quantity=0, buying_power=Decimal(500) * M, buying_power_basis="owner_confirmed", fee_rate=Decimal("0.0015"),
                now=NOW, history_window=(date(2016, 10, 24), date(2026, 10, 23)))
    data.update(changes)
    return RecommendationInputs(**data)


def test_zone_uses_approved_margin_and_explicit_basis():
    zone = compute_zone(base=Decimal(100_000), down=Decimal(80_000), up=Decimal(120_000), price=Decimal(70_000), required_margin=Decimal("0.2"))
    assert (zone.buy_below, zone.fair_value, zone.margin_of_safety, zone.position) == (Decimal(80_000), Decimal(100_000), Decimal("0.3"), "below_buy_zone")
    assert zone.basis == "base_scenario_per_share"


def test_buy_tranche_amount_respects_headroom_tranche_and_fees():
    rec = recommend(inputs())
    assert rec.action == "buy_tranche"
    # growth baseline 50% of 1,000m = 500m headroom; tranche 25% = 125m; cash 500m covers it with fees
    assert rec.amount == Decimal(125) * M
    assert rec.shares is None and rec.quantity_requires_confirmation is True
    assert rec.weight_before == 0 and rec.weight_after == Decimal("0.125")
    assert "doc-bctc-2025" in rec.source_ids and rec.assumption_version == 4


def test_insufficient_cash_after_fees_reduces_amount():
    rec = recommend(inputs(buying_power=Decimal(100) * M))
    assert rec.action == "buy_tranche" and rec.amount == Decimal(100) * M / Decimal("1.0015")
    assert "cash_limited" in rec.constraints


def test_unknown_buying_power_waits():
    rec = recommend(inputs(buying_power=None, buying_power_basis="unknown"))
    assert rec.action == "wait" and "buying_power_unknown" in rec.reasons and rec.amount == 0


@pytest.mark.parametrize("changes, reason", [
    ({"valuation": valuation(status="unavailable", base=None, down=None, up=None)}, "valuation_unavailable"),
    ({"valuation": valuation(status="draft")}, "assumptions_not_approved"),
    ({"price": None}, "price_missing"),
    ({"analysis_gaps": ("governance_not_checked",)}, "analysis_gaps"),
    ({"freshness": profile_freshness(NOW - timedelta(days=40), NOW)}, "profile_reconfirm_required"),
])
def test_missing_basis_returns_insufficient_basis(changes, reason):
    rec = recommend(inputs(**changes))
    assert rec.action == "insufficient_basis" and reason in rec.reasons and rec.amount == 0


def test_low_pb_never_overrides_missing_evidence_or_capacity():
    no_value = recommend(inputs(valuation=valuation(status="unavailable", base=None, down=None, up=None), pb=Decimal("0.5")))
    assert no_value.action == "insufficient_basis"
    capacity = recommend(inputs(risk=risk(q4="A"), pb=Decimal("0.5")))
    assert capacity.action == "wait" and "capacity_blocks_increase" in capacity.reasons and capacity.amount == 0


def test_price_above_buy_zone_waits_with_invalidation_conditions():
    rec = recommend(inputs(price=Decimal(90_000)))
    assert rec.action == "wait" and "price_above_buy_zone" in rec.reasons
    assert "price_above:80000" not in rec.invalidate_conditions  # only for buys


def test_buy_lists_invalidation_conditions():
    rec = recommend(inputs())
    assert set(rec.invalidate_conditions) >= {"price_above:80000", "assumptions_superseded:4", "ledger_or_profile_changed"}


def test_outside_universe_or_removed_never_gets_buy():
    held = recommend(inputs(scope="held_outside_universe", held_quantity=100))
    assert held.action == "hold" and "outside_research_universe" in held.reasons
    removed = recommend(inputs(scope="removed_stop_buy", held_quantity=100))
    assert removed.action == "hold" and "removed_from_universe" in removed.reasons


def test_held_position_above_up_scenario_suggests_reduce_not_order():
    rec = recommend(inputs(price=Decimal(130_000), held_quantity=100))
    assert rec.action == "reduce" and rec.amount == 0 and rec.shares is None


def test_post_trade_portfolio_policy_is_checked():
    near_target = [Position(issuer_id="other", control_group_id="other", industry="bank", market_value=str(Decimal(490) * M))]
    rec = recommend(inputs(holdings=near_target))
    assert rec.amount == Decimal(10) * M  # headroom 10m < tranche 125m
    full = [Position(issuer_id="other", control_group_id="other", industry="bank", market_value=str(Decimal(500) * M))]
    assert recommend(inputs(holdings=full)).action == "wait"


def test_history_window_recorded_exactly():
    rec = recommend(inputs())
    assert rec.history_window == (date(2016, 10, 24), date(2026, 10, 23))
    assert rec.price_date == date(2026, 10, 23) and rec.analysis_time == NOW


def test_buy_suggests_round_lot_quantity_from_market_rules():
    from investment_agent.domain.market_rules import load_market_rules
    rec = recommend(inputs(market_rules=load_market_rules()))
    # 125,000,000 at 70,000 with 0.15% fee: 1,783.3 shares affordable -> 1,700 in round lots
    assert (rec.suggested_shares, rec.lot_kind, rec.rules_version) == (1700, "round", "hose-rules-2026-10-25.1")
    assert rec.shares is None and rec.quantity_requires_confirmation is True


def test_small_amount_falls_back_to_odd_lot():
    from investment_agent.domain.market_rules import load_market_rules
    rec = recommend(inputs(market_rules=load_market_rules(), buying_power=Decimal(5_000_000)))
    assert (rec.suggested_shares, rec.lot_kind) == (71, "odd")


def test_without_rules_no_quantity_is_suggested():
    rec = recommend(inputs())
    assert rec.suggested_shares is None and rec.lot_kind is None
