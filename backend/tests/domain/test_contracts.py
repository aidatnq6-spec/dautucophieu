import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from investment_agent.domain.models import (
    DomainContract,
    EntityIdentity,
    Observation,
    ProvenanceMode,
    QualityStatus,
    SnapshotVersions,
)


def observation(**overrides):
    payload = {
        "entity_id": "entity-001", "metric": "revenue", "period_end": "2025-12-31",
        "published_at": "2026-01-30T09:00:00+07:00",
        "observed_at": "2026-02-01T03:00:00Z", "revision_id": "revision-1",
        "source_id": "source-1", "unit": "VND", "value": "100000000.125",
        "quality_status": "verified", "provenance_mode": "historical_as_reported",
        "missing_reason": None,
    }
    payload.update(overrides)
    return payload


def test_observation_serializes_exact_string_and_aware_time():
    item = Observation.model_validate(observation())
    encoded = json.loads(item.model_dump_json())
    assert encoded["value"] == "100000000.125"
    assert item.observed_at.tzinfo is not None
    assert isinstance(item.period_end.isoformat(), str)


@pytest.mark.parametrize("field", ["published_at", "observed_at"])
def test_observation_rejects_naive_timestamp(field):
    with pytest.raises(ValidationError):
        Observation.model_validate(observation(**{field: "2026-02-01T03:00:00"}))


def test_observation_rejects_float_and_missing_without_reason():
    with pytest.raises(ValidationError):
        Observation.model_validate(observation(value=1.25))
    with pytest.raises(ValidationError):
        Observation.model_validate(observation(value=None, missing_reason=None))
    with pytest.raises(ValidationError):
        Observation.model_validate(observation(value=None, quality_status="missing", missing_reason="  "))
    item = Observation.model_validate(observation(value=None, quality_status="missing", missing_reason="No filing supplied"))
    assert item.value is None
    with pytest.raises(ValidationError):
        Observation.model_validate(observation(value="0", quality_status="missing"))


def test_entity_identity_keeps_canonical_id_distinct_from_ticker():
    assert EntityIdentity(entity_id="entity-001", ticker="ABC", exchange="HOSE").ticker == "ABC"
    with pytest.raises(ValidationError):
        EntityIdentity(entity_id="ABC", ticker="ABC", exchange="HOSE")


def test_versions_are_required_nonempty_and_extra_fields_rejected():
    values = dict(profile_version="p1", portfolio_version="f1", universe_version="u1",
                  data_revision_id="d1", assumption_version="a1", policy_version="r1")
    assert SnapshotVersions.model_validate(values).portfolio_version == "f1"
    with pytest.raises(ValidationError):
        SnapshotVersions.model_validate({**values, "policy_version": ""})
    with pytest.raises(ValidationError):
        SnapshotVersions.model_validate({**values, "surprise": "x"})


def test_schema_export_matches_model_and_declares_boundary_constraints():
    path = Path(__file__).resolve().parents[3] / "contracts" / "domain.schema.json"
    exported = json.loads(path.read_text(encoding="utf-8"))
    assert exported == DomainContract.model_json_schema()
    assert exported["properties"]["contract_version"]["const"] == "1"
    definitions = exported["$defs"]
    assert set(definitions["ProvenanceMode"]["enum"]) == {mode.value for mode in ProvenanceMode}
    assert set(definitions["QualityStatus"]["enum"]) == {status.value for status in QualityStatus}
    assert definitions["Observation"]["properties"]["value"]["anyOf"][0]["type"] == "string"
