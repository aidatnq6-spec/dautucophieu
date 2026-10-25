"""Company documents with checksum, provenance and usage rights; extracted numbers start as candidates.

OCR, parser and LLM extractions are candidates until a check against the
source page confirms the same value; only then do they become verified. A
candidate never replaces a verified number.
"""

import hashlib
from datetime import date
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from investment_agent.domain.models import ContractModel, NonemptyId, SignedAmount


class EvidenceError(ValueError):
    pass


class Document(ContractModel):
    document_id: NonemptyId
    entity_id: NonemptyId
    title: NonemptyId
    kind: Literal["financial_statement", "annual_report", "disclosure", "regulator_decision", "meeting_minutes", "other"]
    source_url: str = Field(pattern=r"^https://\S+$")
    published_at: AwareDatetime | None = None
    published_date: date | None = None
    retrieved_at: AwareDatetime
    version: NonemptyId
    rights: Literal["public_reference", "licensed_internal", "unknown"]
    checksum: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _dated(self):
        if self.published_at is None and self.published_date is None:
            raise ValueError("document needs a publication date")
        return self

    def verify(self, content: bytes):
        if hashlib.sha256(content).hexdigest() != self.checksum:
            raise EvidenceError("checksum_mismatch")


def register_document(content: bytes, **fields) -> Document:
    return Document.model_validate({**fields, "checksum": hashlib.sha256(content).hexdigest()})


class ExtractedValue(ContractModel):
    document_id: NonemptyId
    page: int = Field(strict=True, ge=1)
    table_ref: NonemptyId
    label: NonemptyId
    value: SignedAmount
    unit: Literal["VND", "thousand_VND", "million_VND", "billion_VND", "shares", "percent"]
    method: Literal["manual", "parser", "ocr", "llm"]
    status: Literal["candidate"] = "candidate"
    verified_by: str | None = None


class VerifiedValue(ExtractedValue):
    status: Literal["verified"]
    verified_by: NonemptyId


def verify_extraction(value: ExtractedValue, *, checked_value: str, checked_page: int, checker: str) -> VerifiedValue:
    if checked_page != value.page or format(value.value, "f") != checked_value:
        raise EvidenceError("source_check_mismatch")
    return VerifiedValue.model_validate({**value.model_dump(mode="json"), "status": "verified", "verified_by": checker})
