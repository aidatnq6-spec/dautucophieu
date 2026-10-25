import type { DomainContract } from "../generated/domain";

type Observation = DomainContract["observation"];

export const presentObservation: Observation = {
  entity_id: "entity-1", metric: "revenue", period_end: "2025-12-31",
  published_at: "2026-01-30T09:00:00+07:00", observed_at: "2026-02-01T03:00:00Z",
  revision_id: "revision-1", source_id: "source-1", unit: "VND",
  value: "100", quality_status: "verified", provenance_mode: "historical_as_reported",
};

export const missingObservation: Observation = {
  ...presentObservation, value: null, quality_status: "missing",
  missing_reason: "No filing supplied",
};

// @ts-expect-error A null observation requires a reason.
export const unexplainedMissingObservation: Observation = {
  ...presentObservation, value: null, quality_status: "missing",
};
