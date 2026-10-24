"""Small, versioned contracts shared by market, portfolio, and reporting."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    WithJsonSchema,
    model_validator,
)

from .money import parse_amount, parse_ratio


_UNSIGNED_SCHEMA = {"type": "string", "pattern": r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"}
_SIGNED_SCHEMA = {"type": "string", "pattern": r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"}
_RATIO_SCHEMA = {"type": "string", "pattern": r"^(?:0(?:\.[0-9]+)?|1(?:\.0+)?)$"}

UnsignedAmount = Annotated[
    Decimal, BeforeValidator(parse_amount), PlainSerializer(str, return_type=str),
    WithJsonSchema(_UNSIGNED_SCHEMA),
]
SignedAmount = Annotated[
    Decimal, BeforeValidator(lambda value: parse_amount(value, allow_negative=True)),
    PlainSerializer(str, return_type=str), WithJsonSchema(_SIGNED_SCHEMA),
]
Ratio = Annotated[
    Decimal, BeforeValidator(parse_ratio), PlainSerializer(str, return_type=str),
    WithJsonSchema(_RATIO_SCHEMA),
]
NonemptyId = Annotated[str, Field(strict=True, min_length=1, pattern=r"\S")]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QualityStatus(str, Enum):
    VERIFIED = "verified"
    PROVISIONAL = "provisional"
    STALE = "stale"
    MISSING = "missing"
    INVALID = "invalid"


class ProvenanceMode(str, Enum):
    SYNTHETIC = "synthetic"
    HISTORICAL_AS_REPORTED = "historical_as_reported"
    LATEST_RESTATED = "latest_restated"


class ReportStatus(str, Enum):
    BUILDING = "building"
    VALIDATED = "validated"
    PUBLISHED = "published"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    RETRYABLE = "retryable"
    UNKNOWN = "unknown"
    FAILED = "failed"


class EntityIdentity(ContractModel):
    entity_id: NonemptyId
    ticker: NonemptyId
    exchange: NonemptyId

    @model_validator(mode="after")
    def distinguish_entity_from_ticker(self):
        if self.entity_id == self.ticker:
            raise ValueError("entity_id must be distinct from ticker")
        return self


class Observation(ContractModel):
    entity_id: NonemptyId
    metric: NonemptyId
    period_end: date
    published_at: AwareDatetime
    observed_at: AwareDatetime
    revision_id: NonemptyId
    source_id: NonemptyId
    unit: NonemptyId
    value: SignedAmount | None
    quality_status: QualityStatus
    provenance_mode: ProvenanceMode
    missing_reason: str | None = None

    @model_validator(mode="after")
    def require_missing_reason(self):
        if self.value is None and (self.missing_reason is None or not self.missing_reason.strip()):
            raise ValueError("missing value requires a reason")
        if self.value is not None and self.missing_reason is not None:
            raise ValueError("reason is only valid for missing value")
        if self.value is None and self.quality_status not in {QualityStatus.MISSING, QualityStatus.INVALID}:
            raise ValueError("null value requires missing or invalid quality status")
        if self.value is not None and self.quality_status == QualityStatus.MISSING:
            raise ValueError("missing quality status requires null value")
        return self


class SnapshotVersions(ContractModel):
    profile_version: NonemptyId
    portfolio_version: NonemptyId
    universe_version: NonemptyId
    data_revision_id: NonemptyId
    assumption_version: NonemptyId
    policy_version: NonemptyId


class ApiError(ContractModel):
    code: NonemptyId
    message: NonemptyId
    job_id: NonemptyId | None = None
    correlation_id: NonemptyId | None = None


class DomainContract(ContractModel):
    """Schema entrypoint; each field references one reusable contract."""

    contract_version: Literal["1"]
    entity: EntityIdentity
    observation: Observation
    snapshot_versions: SnapshotVersions
    report_status: ReportStatus
    delivery_status: DeliveryStatus
    api_error: ApiError
    unsigned_amount: UnsignedAmount
    ratio: Ratio
