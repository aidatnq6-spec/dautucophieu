import json
from pathlib import Path
from copy import deepcopy
from dataclasses import replace

import pytest

from investment_agent.market.coverage import audit_case, audit_universe, load_fixture_cases


CASES = load_fixture_cases(Path(__file__).parents[3] / "tests/fixtures/market/coverage_cases.json")


def test_fixture_decisions():
    for case in CASES:
        report = audit_case(case)
        assert report.eligible is case["expect_eligible"], case["name"]
        assert set(case["expect_gaps"]).issubset(set(report.gaps)), case["name"]


def test_duplicate_periods_cannot_inflate_coverage():
    case = next(c for c in CASES if c["name"] == "eligible_transfer")
    case = json.loads(json.dumps(case))
    case["financials"]["annual_periods"] = ["2016"] * 10
    assert "annual_periods" in audit_case(case).gaps


def test_missing_price_range_returns_gaps_instead_of_crashing():
    case = deepcopy(CASES[0])
    case["prices"] = {}
    report = audit_case(case)
    assert report.eligible is False
    assert {"price_years", "price_continuity", "annual_periods"} <= set(report.gaps)


def test_duplicate_among_complete_periods_is_rejected():
    case = deepcopy(CASES[0])
    case["financials"]["annual_periods"].append(case["financials"]["annual_periods"][0])
    assert "annual_periods" in audit_case(case).gaps


def test_reversed_invalid_ratio_interval_is_rejected():
    case = deepcopy(CASES[0])
    case["ratios"]["invalid_intervals"] = [
        {"start": "2021-01-01", "end": "2020-01-01", "reason": "negative_eps"}
    ]
    assert "ratio_invalid_interval_unexplained" in audit_case(case).gaps


def test_isolated_price_endpoints_cannot_prove_continuity():
    case = next(c for c in CASES if c["name"] == "eligible_transfer")
    case = json.loads(json.dumps(case))
    endpoints = [case["prices"]["expected_sessions"][0], case["prices"]["expected_sessions"][-1]]
    case["prices"]["expected_sessions"] = endpoints
    case["prices"]["observed_sessions"] = endpoints
    assert "price_continuity" in audit_case(case).gaps


def test_fixture_is_never_live_evidence():
    case = next(c for c in CASES if c["name"] == "eligible_transfer")
    report = audit_case(case)
    assert report.evidence_kind == "synthetic"
    assert report.live_eligible is False


def test_relabeling_fixture_cannot_create_live_evidence():
    case = deepcopy(CASES[0])
    case["evidence_kind"] = "live"
    case["rights"]["evidence"] = "terms verified"
    assert audit_case(case).live_eligible is False


def test_sparse_dated_rows_do_not_prove_continuity():
    case = deepcopy(CASES[0])
    case["prices"]["observed_sessions"] = case["prices"]["observed_sessions"][:1] + case["prices"]["observed_sessions"][-1:]
    assert "price_continuity" in audit_case(case).gaps


def test_freeform_rights_are_not_record_evidence():
    case = deepcopy(CASES[0])
    case["rights"]["evidence"] = "verified"
    assert "usage_rights" in audit_case(case).gaps


@pytest.mark.parametrize(("change", "gap"), [
    (lambda c: c["financials"]["annual_periods"].append("2027"), "annual_periods"),
    (lambda c: c["financials"].update(annual_periods=[str(y) for y in range(1990, 2000)]), "annual_periods"),
    (lambda c: c["ratios"].update(pb_end="2025-10-24"), "pb_freshness"),
])
def test_periods_and_ratios_align_to_as_of(change, gap):
    case = deepcopy(CASES[0])
    change(case)
    assert gap in audit_case(case).gaps


def test_universe_requires_fifty_distinct_live_hose_issuers():
    reports = [audit_case(deepcopy(CASES[0])) for _ in range(50)]
    aggregate = audit_universe(reports)
    assert aggregate.distinct_structural_issuers == 1
    assert aggregate.distinct_eligible_issuers == 0
    assert aggregate.live_eligible is False
    assert "target_50" in aggregate.gaps


def test_forged_report_flags_cannot_activate_universe():
    report = audit_case(deepcopy(CASES[0]))
    forged = [replace(report, entity_id=f"issuer-{i}", evidence_kind="live", live_eligible=True)
              for i in range(50)]
    aggregate = audit_universe(forged)
    assert aggregate.distinct_structural_issuers == 50
    assert aggregate.distinct_eligible_issuers == 0
    assert aggregate.live_eligible is False


def test_as_of_advances_beyond_observed_calendar():
    case = deepcopy(CASES[0])
    case["as_of"] = "2026-11-02"
    assert "price_continuity" in audit_case(case).gaps


def test_sparse_ratio_rows_cannot_prove_history():
    case = deepcopy(CASES[0])
    case["ratios"]["pe_observed_sessions"] = case["ratios"]["pe_observed_sessions"][::2]
    assert "pe_freshness" in audit_case(case).gaps


def test_rights_record_needs_dated_scope():
    case = deepcopy(CASES[0])
    case["rights"]["evidence"]["inspected_at"] = "unknown"
    assert "usage_rights" in audit_case(case).gaps


@pytest.mark.parametrize(("change", "gap"), [
    (lambda c: c["prices"].update(start="2017-10-25"), "price_years"),
    (lambda c: c["financials"].update(quarter_periods=c["financials"]["quarter_periods"][:-1]), "quarter_periods"),
    (lambda c: c["identity_segments"][0].update(entity_id="another-issuer"), "entity_continuity"),
    (lambda c: c["disclosures"].update(published_at_verified=False), "publication_timestamps"),
    (lambda c: c["capabilities"].update(usage_rights="unknown"), "capability_usage_rights"),
    (lambda c: c["rights"].update(personal_analysis="unknown"), "usage_rights"),
    (lambda c: c["ratios"].update(invalid_intervals=[{"start": "2020-01-01", "end": "2020-02-01"}]), "ratio_invalid_interval_unexplained"),
])
def test_missing_evidence_fails_closed(change, gap):
    case = deepcopy(CASES[0])
    change(case)
    report = audit_case(case)
    assert gap in report.gaps
    assert report.eligible is False
