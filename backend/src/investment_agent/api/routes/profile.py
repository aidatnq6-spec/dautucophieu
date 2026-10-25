from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from investment_agent.domain.investable_capital import FinancialProfile, assess_capital
from investment_agent.domain.models import ContractModel, SignedAmount, UnsignedAmount
from investment_agent.domain.profile import ConfirmedProfile, profile_freshness
from investment_agent.repositories.personal import IdempotencyConflict, RepositoryUnavailable, VersionConflict
from investment_agent.repositories.personal_cache import PersonalView

from ..auth import require_owner

router = APIRouter(prefix="/internal/profile")
COLLECTION, RECORD = "profile_versions", "main"


class AssessmentRequest(ContractModel):
    profile: FinancialProfile
    # Until the Task 11 ledger valuation exists the caller supplies it; None means unknown.
    ledger_value: UnsignedAmount | None


class ConfirmRequest(AssessmentRequest):
    reviewed_net: SignedAmount | None
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _error(status, code, message):
    return JSONResponse({"code": code, "message": message}, status_code=status)


def _unavailable():
    return _error(503, "personal_repository_unavailable", "Chưa kết nối được kho dữ liệu cá nhân; không ghi thay đổi.")


def _now(request: Request) -> datetime:
    return datetime.fromtimestamp(request.app.state.clock(), timezone.utc)


def _view(request: Request, record, *, stale=False):
    stored = ConfirmedProfile.model_validate(record.payload)
    freshness = profile_freshness(stored.confirmed_at, _now(request))
    if stale:
        freshness = freshness.model_copy(update={"allows_new_recommendations": False})
    return {"version": record.version, **stored.model_dump(mode="json"), "freshness": freshness.model_dump(mode="json"), "stale": stale}


@router.post("/assessment")
def preview(request: Request, body: AssessmentRequest):
    require_owner(request)
    return assess_capital(body.profile, ledger_value=body.ledger_value).model_dump(mode="json")


@router.get("")
def current(request: Request):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return _unavailable()
    try:
        result = repo.read(owner, COLLECTION, RECORD)
    except RepositoryUnavailable:
        return _unavailable()
    stale = False
    if isinstance(result, PersonalView):
        result, stale = result.record, result.stale
    if result is None:
        return _error(404, "profile_missing", "Chưa có hồ sơ tài chính đã xác nhận.")
    return _view(request, result, stale=stale)


@router.put("")
def confirm(request: Request, body: ConfirmRequest):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return _unavailable()
    assessment = assess_capital(body.profile, ledger_value=body.ledger_value)
    if assessment.status in {"needs_confirmation", "incomplete"}:
        return _error(422, "profile_not_confirmable", "Cần xác nhận mục tiêu và giá trị sổ trước khi chốt vốn có thể đầu tư.")
    if body.reviewed_net != assessment.net:
        return _error(409, "capital_changed", "Bảng tính vốn đã thay đổi; hãy xem lại trước khi xác nhận.")
    stored = ConfirmedProfile(profile=body.profile, assessment=assessment, confirmed_at=_now(request))
    try:
        record = repo.write(owner, COLLECTION, RECORD, stored.model_dump(mode="json"),
                            expected_version=body.expected_version, request_id=body.request_id)
    except VersionConflict:
        return _error(409, "version_conflict", "Hồ sơ đã được cập nhật ở nơi khác; hãy tải lại.")
    except IdempotencyConflict:
        return _error(409, "request_reused", "Mã yêu cầu đã dùng cho nội dung khác.")
    except RepositoryUnavailable:
        return _unavailable()
    return _view(request, record)
