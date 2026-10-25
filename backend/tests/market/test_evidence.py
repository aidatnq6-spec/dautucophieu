from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from investment_agent.market.disclosures import Document, ExtractedValue, EvidenceError, register_document, verify_extraction
from investment_agent.market.evidence import GovernanceEvidence, build_analysis_pack, governance_summary
from investment_agent.market.industry import industry_aggregate
from investment_agent.market.macro import MacroObservation, MacroVintages

T0 = datetime(2026, 1, 6, 9, tzinfo=timezone.utc)
T1 = datetime(2026, 3, 1, 9, tzinfo=timezone.utc)


def macro(value, vintage, released, series="gdp_growth_yoy"):
    return MacroObservation(series_id=series, period="2025Q4", value=value, unit="percent", source_id="gso",
                            source_url="https://www.gso.gov.vn/example", released_at=released, vintage_id=vintage, provenance_mode="synthetic")


def test_macro_revision_keeps_old_vintage():
    store = MacroVintages()
    store.add(macro("7.1", "v1", T0))
    store.add(macro("7.4", "v2", T1))
    assert store.latest("gdp_growth_yoy", "2025Q4").value == Decimal("7.4")
    assert store.as_of("gdp_growth_yoy", "2025Q4", datetime(2026, 2, 1, tzinfo=timezone.utc)).value == Decimal("7.1")
    assert [o.vintage_id for o in store.history("gdp_growth_yoy", "2025Q4")] == ["v1", "v2"]


def test_macro_vintage_retry_idempotent_but_conflict_rejected():
    store = MacroVintages()
    store.add(macro("7.1", "v1", T0))
    store.add(macro("7.1", "v1", T0))
    assert len(store.history("gdp_growth_yoy", "2025Q4")) == 1
    with pytest.raises(EvidenceError):
        store.add(macro("7.2", "v1", T0))


def test_macro_requires_https_source_and_aware_time():
    with pytest.raises(ValidationError):
        MacroObservation.model_validate({**macro("7.1", "v1", T0).model_dump(mode="json"), "source_url": "ftp://x"})
    with pytest.raises(ValidationError):
        MacroObservation.model_validate({**macro("7.1", "v1", T0).model_dump(mode="json"), "released_at": "2026-01-06T09:00:00"})


def test_document_registration_records_checksum_and_rejects_tampering():
    content = b"%PDF synthetic annual report"
    doc = register_document(content, document_id="doc-1", entity_id="ent-fpt", title="BCTC 2025", kind="financial_statement",
                            source_url="https://example.vn/bctc-2025.pdf", published_date="2026-03-30", retrieved_at=T1,
                            version="1", rights="public_reference")
    assert len(doc.checksum) == 64
    doc.verify(content)
    with pytest.raises(EvidenceError):
        doc.verify(content + b"x")


def test_document_requires_source_url_date_and_version():
    with pytest.raises(ValidationError):
        Document.model_validate({"document_id": "d", "entity_id": "e", "title": "t", "kind": "financial_statement",
                                 "source_url": "https://x.vn/a.pdf", "retrieved_at": T1.isoformat(), "version": "1",
                                 "rights": "unknown", "checksum": "0" * 64})


def extracted(method, **changes):
    data = {"document_id": "doc-1", "page": 12, "table_ref": "B01-DN", "label": "Lợi nhuận sau thuế", "value": "1234",
            "unit": "million_VND", "method": method}
    data.update(changes)
    return ExtractedValue.model_validate(data)


@pytest.mark.parametrize("method", ["ocr", "llm", "parser"])
def test_machine_extractions_start_as_candidates(method):
    assert extracted(method).status == "candidate"


def test_candidate_is_verified_only_against_matching_source_check():
    value = extracted("llm")
    with pytest.raises(EvidenceError):
        verify_extraction(value, checked_value="1235", checked_page=12, checker="owner")
    with pytest.raises(EvidenceError):
        verify_extraction(value, checked_value="1234", checked_page=13, checker="owner")
    verified = verify_extraction(value, checked_value="1234", checked_page=12, checker="owner")
    assert verified.status == "verified" and verified.verified_by == "owner"


def test_extraction_cannot_claim_verified_on_creation():
    with pytest.raises(ValidationError):
        extracted("llm", status="verified")


def test_extraction_needs_unit_and_page():
    with pytest.raises(ValidationError):
        extracted("manual", page=0)


def evidence(eid, classification, topic="sanction", **changes):
    data = {"evidence_id": eid, "entity_id": "ent-fpt", "topic": topic, "classification": classification,
            "summary": "Quyết định xử phạt công bố thông tin chậm", "source_url": "https://ssc.gov.vn/example", "event_date": "2025-05-05",
            "company_response": None, "assessed_by_ai": False}
    data.update(changes)
    return GovernanceEvidence.model_validate(data)


def test_no_findings_never_becomes_an_integrity_label():
    summary = governance_summary("ent-fpt", [], sources_checked=["ssc.gov.vn", "hsx.vn"])
    assert summary.status == "no_records_found_in_sources_checked"
    assert summary.sources_checked == ("ssc.gov.vn", "hsx.vn")
    assert "integrity" not in summary.model_dump_json() and "clean" not in summary.model_dump_json()


def test_unchecked_sources_is_a_gap_not_a_result():
    assert governance_summary("ent-fpt", [], sources_checked=[]).status == "not_checked"


def test_findings_are_grouped_by_classification_with_company_response():
    items = [evidence("e1", "official"), evidence("e2", "disputed", company_response="Doanh nghiệp đã khiếu nại"),
             evidence("e3", "unverified", assessed_by_ai=True)]
    summary = governance_summary("ent-fpt", items, sources_checked=["ssc.gov.vn"])
    assert summary.status == "findings_recorded"
    assert summary.counts == {"official": 1, "disputed": 1, "unverified": 1}
    assert summary.ai_assessed_ids == ("e3",)
    assert next(f for f in summary.findings if f.evidence_id == "e2").company_response


def test_industry_aggregate_reports_sample_and_coverage_not_whole_industry():
    agg = industry_aggregate("bank", "revenue_growth_yoy", {"ent-a": Decimal("0.10"), "ent-b": Decimal("0.20"), "ent-c": None},
                             population=27)
    assert (agg.sample_count, agg.missing_count, agg.population) == (2, 1, 27)
    assert agg.coverage == Decimal(2) / Decimal(27)
    assert agg.claim_scope == "sample_only" and agg.median == Decimal("0.15")


def test_industry_aggregate_without_known_population_has_unknown_coverage():
    agg = industry_aggregate("bank", "revenue_growth_yoy", {"ent-a": Decimal("0.10")}, population=None)
    assert agg.coverage is None and agg.claim_scope == "sample_only"


def test_analysis_pack_separates_facts_and_gaps():
    store = MacroVintages()
    store.add(macro("7.1", "v1", T0))
    agg = industry_aggregate("bank", "revenue_growth_yoy", {"ent-a": Decimal("0.10")}, population=None)
    pack = build_analysis_pack("ent-fpt", industry="bank", macro=store, macro_series=["gdp_growth_yoy", "cpi_yoy"], period="2025Q4",
                               as_of=T1, industry_aggregates=[agg], governance=governance_summary("ent-fpt", [], sources_checked=[]))
    assert [m.series_id for m in pack.macro_facts] == ["gdp_growth_yoy"]
    assert set(pack.gaps) == {"macro_missing:cpi_yoy", "industry_coverage_unknown:revenue_growth_yoy", "governance_not_checked"}
