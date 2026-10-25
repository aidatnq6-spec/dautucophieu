from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from investment_agent.market.asof import available_from, facts_as_of
from investment_agent.market.calendar import TradingCalendar
from investment_agent.market.financials import FinancialFact
from investment_agent.market.prices import AdjustmentFactor
from investment_agent.market.ratios import price_to_book, price_to_earnings, ttm_eps

CAL = TradingCalendar(version="t", source="synthetic", holidays=frozenset(), first=date(2024, 1, 1), last=date(2026, 12, 31))
QUARTERS = [("2025Q1", "2025-03-31"), ("2025Q2", "2025-06-30"), ("2025Q3", "2025-09-30"), ("2025Q4", "2025-12-31"), ("2026Q1", "2026-03-31")]


def at(day, hour=10):
    return datetime.fromisoformat(f"{day}T{hour:02d}:00:00+07:00")


def fact(metric, label, end, value, published, *, period_type="quarter", scope="consolidated", revision="r1", unit="VND", **extra):
    data = {"entity_id": "ent-fpt", "metric": metric, "period_type": period_type, "fiscal_label": label, "period_end": end,
            "statement_scope": scope, "value": str(value), "unit": unit, "revision_id": revision, "source_id": "fixture",
            "provenance_mode": "synthetic", "derived": False}
    if isinstance(published, datetime):
        data["published_at"] = published.isoformat()
    elif published is not None:
        data["published_date"] = published
    data.update(extra)
    return FinancialFact.model_validate(data)


def quarters(values=(100, 110, 120, 130, 140), shares=1000, equity=5000):
    out = []
    for (label, end), v in zip(QUARTERS, values):
        pub = at(f"{end[:4]}-{int(end[5:7]) % 12 + 1:02d}-20" if end[5:7] != "12" else f"{int(end[:4]) + 1}-01-20")
        out += [fact("net_income_parent", label, end, v, pub), fact("shares_outstanding", label, end, shares, pub),
                fact("equity_parent", label, end, equity, pub)]
    return out


def test_report_published_after_valuation_time_is_not_used():
    facts = quarters()
    before_q1_2026 = facts_as_of(facts, at("2026-04-19"), CAL, mode="historical_as_reported")
    eps = ttm_eps(before_q1_2026, "ent-fpt")
    assert eps.inputs_period_labels == ("2025Q1", "2025Q2", "2025Q3", "2025Q4")
    assert eps.value == Decimal(460) / 1000


def test_later_revision_does_not_rewrite_the_past():
    facts = quarters() + [fact("net_income_parent", "2025Q4", "2025-12-31", 30, at("2026-06-01"), revision="r2")]
    before = ttm_eps(facts_as_of(facts, at("2026-05-01"), CAL, mode="historical_as_reported"), "ent-fpt")
    after = ttm_eps(facts_as_of(facts, at("2026-06-02"), CAL, mode="historical_as_reported"), "ent-fpt")
    assert before.value == Decimal(130 + 120 + 140 + 110) / 1000
    assert after.value == Decimal(30 + 120 + 140 + 110) / 1000


def test_date_only_publication_applies_from_next_session():
    f = fact("net_income_parent", "2025Q1", "2025-03-31", 1, "2025-04-18")  # Friday
    assert available_from(f, CAL) == at("2025-04-21", 0).replace(hour=0)
    assert not facts_as_of([f], at("2025-04-18", 23), CAL, mode="historical_as_reported")
    assert facts_as_of([f], at("2025-04-21", 9), CAL, mode="historical_as_reported")


def test_missing_publication_time_blocks_as_reported_but_allows_labelled_restated():
    f = fact("net_income_parent", "2025Q1", "2025-03-31", 1, None, provenance_mode="historical_as_reported")
    assert facts_as_of([f], at("2026-01-01"), CAL, mode="historical_as_reported") == []
    restated = facts_as_of([f], at("2026-01-01"), CAL, mode="latest_restated")
    assert restated and restated[0].provenance_mode == "latest_restated"


def test_ttm_never_adds_annual_into_quarters():
    facts = [f for f in quarters() if f.fiscal_label != "2025Q4"]
    facts.append(fact("net_income_parent", "2025FY", "2025-12-31", 500, at("2026-01-20"), period_type="annual"))
    eps = ttm_eps(facts_as_of(facts, at("2026-04-19"), CAL, mode="historical_as_reported"), "ent-fpt")
    assert eps.value is None and eps.reason == "quarters_missing"


def test_derived_fourth_quarter_is_usable_and_labelled():
    facts = [f for f in quarters() if not (f.fiscal_label == "2025Q4" and f.metric == "net_income_parent")]
    facts.append(fact("net_income_parent", "2025Q4", "2025-12-31", 130, at("2026-01-20"), derived=True))
    eps = ttm_eps(facts_as_of(facts, at("2026-04-19"), CAL, mode="historical_as_reported"), "ent-fpt")
    assert eps.value == Decimal(460) / 1000 and eps.derived_inputs is True


def test_consolidated_and_separate_are_not_mixed():
    facts = [f for f in quarters() if not (f.fiscal_label == "2025Q2" and f.metric == "net_income_parent")]
    facts.append(fact("net_income_parent", "2025Q2", "2025-06-30", 110, at("2025-07-20"), scope="separate"))
    eps = ttm_eps(facts_as_of(facts, at("2026-04-19"), CAL, mode="historical_as_reported"), "ent-fpt")
    assert eps.value is None and eps.reason == "quarters_missing"


def test_complete_separate_scope_does_not_fill_incomplete_consolidated():
    facts = [f for f in quarters() if not (f.fiscal_label == "2025Q2" and f.metric == "net_income_parent")]
    facts += [f.model_copy(update={"statement_scope": "separate"}) for f in quarters()]
    eps = ttm_eps(facts_as_of(facts, at("2026-04-19"), CAL, mode="historical_as_reported"), "ent-fpt")
    assert eps.value is None and eps.reason == "quarters_missing"


def test_thousand_vnd_units_are_normalised():
    f = fact("net_income_parent", "2025Q1", "2025-03-31", "1.5", at("2025-04-20"), unit="thousand_VND")
    assert f.value == Decimal(1500) and f.unit == "VND"


def test_non_positive_eps_or_equity_is_unavailable_not_cheap():
    losses = quarters(values=(-100, -10, 5, 10, 20))
    asof = facts_as_of(losses, at("2026-04-19"), CAL, mode="historical_as_reported")
    pe = price_to_earnings(Decimal(20_000), asof, "ent-fpt", valuation_date=date(2026, 4, 17), share_actions=[])
    assert pe.value is None and pe.reason == "non_positive_eps"
    negative_equity = facts_as_of(quarters(equity=-1), at("2026-04-19"), CAL, mode="historical_as_reported")
    pb = price_to_book(Decimal(20_000), negative_equity, "ent-fpt", valuation_date=date(2026, 4, 17), share_actions=[])
    assert pb.value is None and pb.reason == "non_positive_equity"


def test_share_basis_follows_post_period_split_so_raw_price_is_consistent():
    asof = facts_as_of(quarters(), at("2026-04-19"), CAL, mode="historical_as_reported")
    split = AdjustmentFactor(entity_id="ent-fpt", action_id="split", ex_date="2026-02-02", factor="0.5", kind="split", source_id="fixture")
    pe = price_to_earnings(Decimal(10_000), asof, "ent-fpt", valuation_date=date(2026, 4, 17), share_actions=[split])
    assert pe.value == Decimal(10_000) / (Decimal(460) / 2000)
    assert pe.share_basis == Decimal(2000) and "split" in pe.inputs
    pb = price_to_book(Decimal(10_000), asof, "ent-fpt", valuation_date=date(2026, 4, 17), share_actions=[split])
    assert pb.value == Decimal(10_000) / (Decimal(5000) / 2000)


def test_restated_facts_never_qualify_as_reported():
    f = fact("net_income_parent", "2025Q1", "2025-03-31", 1, at("2025-04-20"), provenance_mode="latest_restated")
    assert facts_as_of([f], at("2026-01-01"), CAL, mode="historical_as_reported") == []


def test_ratio_records_method_mode_and_inputs():
    asof = facts_as_of(quarters(), at("2026-04-19"), CAL, mode="historical_as_reported")
    pe = price_to_earnings(Decimal(20_000), asof, "ent-fpt", valuation_date=date(2026, 4, 17), share_actions=[])
    assert pe.method_version == "pe_ttm_v1" and pe.provenance_mode == "synthetic"  # fixtures stay labelled synthetic
    assert len(pe.inputs) >= 5


def test_mixed_provenance_modes_are_rejected():
    asof = facts_as_of(quarters(), at("2026-04-19"), CAL, mode="historical_as_reported")
    restated = facts_as_of([fact("shares_outstanding", "2025Q4", "2025-12-31", 1000, None, revision="x", provenance_mode="latest_restated")],
                           at("2026-04-19"), CAL, mode="latest_restated")
    with pytest.raises(ValueError):
        ttm_eps(asof + restated, "ent-fpt")
