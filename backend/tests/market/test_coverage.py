import json
from pathlib import Path
from copy import deepcopy

import pytest

from investment_agent.market.coverage import audit_case


CASES = json.loads((Path(__file__).parents[3] / "tests/fixtures/market/coverage_cases.json").read_text())


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


def test_isolated_price_endpoints_cannot_prove_continuity():
    case = next(c for c in CASES if c["name"] == "eligible_transfer")
    case = json.loads(json.dumps(case))
    case["prices"]["continuity_verified"] = False
    assert "price_continuity" in audit_case(case).gaps


def test_fixture_is_never_live_evidence():
    case = next(c for c in CASES if c["name"] == "eligible_transfer")
    report = audit_case(case)
    assert report.evidence_kind == "synthetic"
    assert report.live_eligible is False


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
