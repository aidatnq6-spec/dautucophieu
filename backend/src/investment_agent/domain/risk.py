"""Versioned 13-question composite survey; capacity flags stay independent of the score.

The questionnaire is a draft accepted for content, not a validated psychometric
instrument. Each version is pinned by a digest of its parsed content, so an
edited file must ship under a new version instead of silently re-scoring.
"""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

from .investable_capital import CapitalAssessment
from .models import ContractModel

QUESTIONNAIRE_PATH = Path(__file__).resolve().parents[4] / "config" / "risk-questionnaire.vi.json"
PINNED_DIGESTS = {
    "risk-vi-2026-10-24.1": "55245f23afdcc55e2785b071a4178f1971d208d17f4857a6c45f0f9424a60048",
}
BOUNDS = ((19, "very_safe"), (26, "cautious"), (33, "moderately_cautious"),
          (40, "balanced"), (46, "growth"), (52, "strong_growth"))
Choice = Literal["A", "B", "C", "D"]
POINTS = {"A": 1, "B": 2, "C": 3, "D": 4}
CONFLICTS = ("answer_conflict_loss_tolerance", "profile_conflict_emergency")


class InvalidQuestionnaire(ValueError):
    pass


class InvalidRiskAnswers(ValueError):
    pass


class Option(ContractModel):
    key: Choice
    points: int
    text: str


class Question(ContractModel):
    id: int
    text: str
    options: tuple[Option, Option, Option, Option]


class Group(ContractModel):
    group: str
    label: str
    min: int
    max: int


class Questionnaire(ContractModel):
    version: str
    digest: str = ""
    language: Literal["vi"]
    validation_status: Literal["draft_unvalidated"]
    notice: str
    notes: dict[str, str]
    groups: tuple[Group, ...]
    questions: tuple[Question, ...]


class RiskAnswer(ContractModel):
    question: int = Field(strict=True, ge=1, le=13)
    answer: Choice


class RiskFlag(ContractModel):
    code: Literal["capacity_shortfall", "emergency_review", "near_term_money", *CONFLICTS]
    questions: tuple[int, ...]
    effect: Literal["block_capital_increase", "review", "separate_near_term_money", "confirm"]


class RiskAssessment(ContractModel):
    questionnaire_version: str
    questionnaire_digest: str
    validation_status: Literal["draft_unvalidated"]
    answers: tuple[RiskAnswer, ...]
    total: int
    group: str
    flags: tuple[RiskFlag, ...]
    confirmed_conflicts: tuple[str, ...]
    unresolved_conflicts: tuple[str, ...]
    blocks_capital_increase: bool
    ready_for_allocation: bool


def _content_digest(data: dict) -> str:
    # Parsed content, so Git line-ending conversion cannot change the digest.
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_questionnaire(path: Path = QUESTIONNAIRE_PATH) -> Questionnaire:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        questionnaire = Questionnaire.model_validate(data)
    except (OSError, ValueError) as exc:
        raise InvalidQuestionnaire("Questionnaire unreadable") from exc
    digest = _content_digest(data)
    if PINNED_DIGESTS.get(questionnaire.version) != digest:
        raise InvalidQuestionnaire("Questionnaire content does not match its pinned version")
    ids = [q.id for q in questionnaire.questions]
    if ids != list(range(1, 14)) or any([o.key for o in q.options] != list("ABCD") or [o.points for o in q.options] != [1, 2, 3, 4]
                                        for q in questionnaire.questions):
        raise InvalidQuestionnaire("Questionnaire must have 13 questions scored A=1..D=4")
    if [(g.max, g.group) for g in questionnaire.groups] != list(BOUNDS):
        raise InvalidQuestionnaire("Questionnaire groups differ from the approved bounds")
    return questionnaire.model_copy(update={"digest": digest})


def classify_total(total: int) -> str:
    if type(total) is not int or not 13 <= total <= 52:
        raise ValueError("invalid risk score")
    return next(group for maximum, group in BOUNDS if total <= maximum)


def assess_risk(questionnaire: Questionnaire, answers: list[dict], *, capital: CapitalAssessment | None = None,
                confirmed_conflicts: list[str] | tuple[str, ...] = ()) -> RiskAssessment:
    try:
        parsed = sorted((RiskAnswer.model_validate(item) for item in answers), key=lambda a: a.question)
    except ValidationError:
        raise InvalidRiskAnswers("Each answer needs a question 1-13 and one of A-D") from None
    if [a.question for a in parsed] != list(range(1, 14)):
        raise InvalidRiskAnswers("Exactly one answer per question is required")
    if any(code not in CONFLICTS for code in confirmed_conflicts):
        raise InvalidRiskAnswers("Unknown conflict confirmation")
    choice = {a.question: a.answer for a in parsed}

    flags = []
    if low := tuple(q for q in (4, 7) if choice[q] == "A"):
        flags.append(RiskFlag(code="capacity_shortfall", questions=low, effect="block_capital_increase"))
    if choice[6] == "A":
        flags.append(RiskFlag(code="emergency_review", questions=(6,), effect="review"))
    if soon := tuple(q for q in (2, 3) if choice[q] == "A"):
        flags.append(RiskFlag(code="near_term_money", questions=soon, effect="separate_near_term_money"))
    if choice[10] == "A" and (bold := tuple(q for q in (11, 13) if choice[q] == "D")):
        flags.append(RiskFlag(code="answer_conflict_loss_tolerance", questions=(10, *bold), effect="confirm"))
    weak_reserve = capital is not None and any(w.code in {"emergency_reserve_shortfall", "emergency_reserve_not_liquid"} for w in capital.warnings)
    if weak_reserve and choice[6] in {"C", "D"}:
        flags.append(RiskFlag(code="profile_conflict_emergency", questions=(6,), effect="confirm"))

    unresolved = tuple(f.code for f in flags if f.effect == "confirm" and f.code not in confirmed_conflicts)
    blocks = any(f.effect == "block_capital_increase" for f in flags)
    total = sum(POINTS[a.answer] for a in parsed)
    return RiskAssessment(
        questionnaire_version=questionnaire.version, questionnaire_digest=questionnaire.digest,
        validation_status=questionnaire.validation_status, answers=tuple(parsed), total=total, group=classify_total(total),
        flags=tuple(flags), confirmed_conflicts=tuple(sorted(set(confirmed_conflicts))), unresolved_conflicts=unresolved,
        blocks_capital_increase=blocks, ready_for_allocation=not unresolved,
    )
