from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.profile import ConfirmedProfile
from investment_agent.domain.allocation import load_allocation_policy
from investment_agent.domain.risk import BOUNDS, InvalidRiskAnswers, assess_risk, load_questionnaire
from investment_agent.repositories.personal import IdempotencyConflict, RepositoryUnavailable
from investment_agent.services.records import RISK_OVERRIDE, RiskOverride, StoredRisk, risk_override

from ..auth import require_owner
from .common import WRITE_ERRORS, committed_retry, error, now, read_current, unavailable, write_error

router = APIRouter(prefix="/internal/risk")
COLLECTION, RECORD = "risk_versions", "main"


class AnswersRequest(ContractModel):
    # Shape is checked by assess_risk so every malformed answer maps to one error code.
    answers: list[dict]
    confirmed_conflicts: list[str] = []


class SaveRequest(AnswersRequest):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _invalid():
    return error(422, "invalid_risk_answers", "Cần trả lời đủ 13 câu, mỗi câu một đáp án A–D.")


def score_range(group: str) -> list[int]:
    """Scores that classify into this group (13 answers scored 1–4, so 13–52 overall)."""
    floor = 13
    for maximum, name in BOUNDS:
        if name == group:
            return [floor, maximum]
        floor = maximum + 1
    raise ValueError(group)


def _view(record, *, stale=False, chosen: RiskOverride | None = None, chosen_version: int = 0):
    stored = StoredRisk.model_validate(record.payload)
    group = chosen.group if chosen and chosen.group else stored.assessment.group
    return {"version": record.version, **stored.model_dump(mode="json"), "stale": stale,
            "override": {"group": chosen.group, "version": chosen_version} if chosen and chosen.group else None,
            "override_version": chosen_version,
            "effective": {"group": group, "manual": bool(chosen and chosen.group), "score_range": score_range(group),
                          "equity_ratio": str(load_allocation_policy().baseline_equity[group])}}


class OverrideRequest(ContractModel):
    group: str | None
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


@router.put("/override")
def put_override(request: Request, body: OverrideRequest):
    """Choose the risk group by hand (it replaces the survey group everywhere), or send null to use the survey again."""
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        chosen = RiskOverride(group=body.group)
    except ValueError:
        return error(422, "invalid_risk_group", "Nhóm khẩu vị không hợp lệ.")
    try:
        record = repo.write(owner, *RISK_OVERRIDE, chosen.model_dump(mode="json"), expected_version=body.expected_version, request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return {"override_version": record.version, "group": chosen.group}


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
    try:
        chosen, chosen_version = risk_override(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    return _view(record, stale=stale, chosen=chosen, chosen_version=chosen_version)


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
    except IdempotencyConflict as exc:
        record = committed_retry(repo, owner, COLLECTION, RECORD, body.expected_version, body.request_id)
        if record is None:
            return write_error(exc)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return _view(record)
