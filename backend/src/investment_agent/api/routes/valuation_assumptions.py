from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import IdempotencyConflict, RepositoryUnavailable, VersionConflict
from investment_agent.valuation.assumptions import ValuationAssumptions, approve_assumptions
from investment_agent.valuation.dcf import value_assumptions

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, read_version, unavailable, write_error

router = APIRouter(prefix="/internal/valuation")
COLLECTION = "valuation_assumptions"


class DraftRequest(ContractModel):
    assumptions: ValuationAssumptions
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class ApproveRequest(ContractModel):
    draft_version: int = Field(strict=True, ge=1)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(record):
    a = ValuationAssumptions.model_validate(record.payload["assumptions"])
    return {"version": record.version, "assumptions": a.model_dump(mode="json"),
            "valuation": value_assumptions(a).model_dump(mode="json"),
            "last_approved_version": record.payload.get("last_approved_version")}


def _repo(request):
    return require_owner(request), request.app.state.personal_repository


@router.get("/{entity_id}")
def current(request: Request, entity_id: str):
    owner, repo = _repo(request)
    if repo is None:
        return unavailable()
    try:
        record = read_version(repo, owner, COLLECTION, entity_id, None)
    except RepositoryUnavailable:
        return unavailable()
    if record is None:
        return error(404, "assumptions_missing", "Chưa có giả định định giá cho mã này.")
    return _view(record)


@router.put("/{entity_id}/draft")
def save_draft(request: Request, entity_id: str, body: DraftRequest):
    owner, repo = _repo(request)
    if repo is None:
        return unavailable()
    if body.assumptions.status != "draft":
        return error(422, "approval_via_endpoint_only", "Chỉ duyệt giả định qua thao tác duyệt của chủ sở hữu.")
    if body.assumptions.entity_id != entity_id:
        return error(422, "entity_mismatch", "Giả định không thuộc mã này.")
    try:
        head = read_version(repo, owner, COLLECTION, entity_id, body.expected_version) if body.expected_version else None
        last = head.payload.get("last_approved_version") if head else None
        if head and head.payload["assumptions"]["status"] == "approved":
            last = head.version
        record = repo.write(owner, COLLECTION, entity_id, {"assumptions": body.assumptions.model_dump(mode="json"), "last_approved_version": last},
                            expected_version=body.expected_version, request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return _view(record)


@router.post("/{entity_id}/approve")
def approve(request: Request, entity_id: str, body: ApproveRequest):
    owner, repo = _repo(request)
    if repo is None:
        return unavailable()
    try:
        draft = read_version(repo, owner, COLLECTION, entity_id, body.draft_version)
        if draft is None:
            return error(404, "assumptions_missing", "Không tìm thấy bản nháp.")
        a = ValuationAssumptions.model_validate(draft.payload["assumptions"])
        if a.status != "draft":
            return error(409, "not_a_draft", "Phiên bản này không phải bản nháp.")
        approved = approve_assumptions(a, actor="owner", now=now(request))
        record = repo.write(owner, COLLECTION, entity_id, {"assumptions": approved.model_dump(mode="json"), "last_approved_version": body.draft_version + 1},
                            expected_version=body.draft_version, request_id=body.request_id)
    except IdempotencyConflict:
        # A retry carries a later approval time; if this request already committed, return that approval.
        head = read_version(repo, owner, COLLECTION, entity_id, body.draft_version + 1)
        if head is not None and head.request_id == body.request_id:
            return _view(head)
        return write_error(IdempotencyConflict())
    except VersionConflict:
        return error(409, "draft_changed", "Bản nháp đã thay đổi sau khi xem; hãy xem lại trước khi duyệt.")
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return _view(record)
