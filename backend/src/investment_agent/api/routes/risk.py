from fastapi import APIRouter, Request
from pydantic import AwareDatetime, Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.profile import ConfirmedProfile
from investment_agent.domain.risk import InvalidRiskAnswers, RiskAssessment, assess_risk, load_questionnaire
from investment_agent.repositories.personal import RepositoryUnavailable

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, read_current, unavailable, write_error

router = APIRouter(prefix="/internal/risk")
COLLECTION, RECORD = "risk_versions", "main"


class AnswersRequest(ContractModel):
    # Shape is checked by assess_risk so every malformed answer maps to one error code.
    answers: list[dict]
    confirmed_conflicts: list[str] = []


class SaveRequest(AnswersRequest):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class StoredRisk(ContractModel):
    schema_version: str = "1"
    assessment: RiskAssessment
    assessed_at: AwareDatetime
    profile_version: int | None


def _invalid():
    return error(422, "invalid_risk_answers", "Cần trả lời đủ 13 câu, mỗi câu một đáp án A–D.")


def _view(record, *, stale=False):
    return {"version": record.version, **StoredRisk.model_validate(record.payload).model_dump(mode="json"), "stale": stale}


@router.get("/questionnaire")
def questionnaire(request: Request):
    require_owner(request)
    return load_questionnaire().model_dump(mode="json")


@router.post("/assessment")
def preview(request: Request, body: AnswersRequest):
    """Answers only; conflicts with the stored profile are evaluated on save."""
    require_owner(request)
    try:
        return assess_risk(load_questionnaire(), body.answers, confirmed_conflicts=body.confirmed_conflicts).model_dump(mode="json")
    except InvalidRiskAnswers:
        return _invalid()


@router.get("")
def current(request: Request):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        record, stale = read_current(repo, owner, COLLECTION, RECORD)
    except RepositoryUnavailable:
        return unavailable()
    if record is None:
        return error(404, "risk_missing", "Chưa có kết quả khảo sát rủi ro.")
    return _view(record, stale=stale)


@router.put("")
def save(request: Request, body: SaveRequest):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        profile, stale = read_current(repo, owner, "profile_versions", "main")
    except RepositoryUnavailable:
        return unavailable()
    if stale:
        return unavailable()  # A cached profile cannot settle a conflict check.
    capital = ConfirmedProfile.model_validate(profile.payload).assessment if profile else None
    try:
        assessment = assess_risk(load_questionnaire(), body.answers, capital=capital, confirmed_conflicts=body.confirmed_conflicts)
    except InvalidRiskAnswers:
        return _invalid()
    stored = StoredRisk(assessment=assessment, assessed_at=now(request), profile_version=profile.version if profile else None)
    try:
        record = repo.write(owner, COLLECTION, RECORD, stored.model_dump(mode="json"),
                            expected_version=body.expected_version, request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return _view(record)
