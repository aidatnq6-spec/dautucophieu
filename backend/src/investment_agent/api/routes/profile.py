from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.investable_capital import FinancialProfile, assess_capital
from investment_agent.domain.models import ContractModel, SignedAmount, UnsignedAmount
from investment_agent.domain.profile import ConfirmedProfile, profile_freshness
from investment_agent.repositories.personal import RepositoryUnavailable

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, read_current, unavailable, write_error

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


def _view(request: Request, record, *, stale=False):
    stored = ConfirmedProfile.model_validate(record.payload)
    freshness = profile_freshness(stored.confirmed_at, now(request))
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
        return unavailable()
    try:
        result, stale = read_current(repo, owner, COLLECTION, RECORD)
    except RepositoryUnavailable:
        return unavailable()
    if result is None:
        return error(404, "profile_missing", "Chưa có hồ sơ tài chính đã xác nhận.")
    return _view(request, result, stale=stale)


@router.put("")
def confirm(request: Request, body: ConfirmRequest):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    assessment = assess_capital(body.profile, ledger_value=body.ledger_value)
    if assessment.status in {"needs_confirmation", "incomplete"}:
        return error(422, "profile_not_confirmable", "Cần xác nhận mục tiêu và giá trị sổ trước khi chốt vốn có thể đầu tư.")
    if body.reviewed_net != assessment.net:
        return error(409, "capital_changed", "Bảng tính vốn đã thay đổi; hãy xem lại trước khi xác nhận.")
    stored = ConfirmedProfile(profile=body.profile, assessment=assessment, confirmed_at=now(request))
    try:
        record = repo.write(owner, COLLECTION, RECORD, stored.model_dump(mode="json"),
                            expected_version=body.expected_version, request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return _view(request, record)
