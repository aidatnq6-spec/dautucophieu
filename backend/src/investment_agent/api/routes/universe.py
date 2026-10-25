from datetime import date

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.market.universe import (
    Candidate, Proposal, UniverseError, UniverseVersion, approve, build_proposal, load_universe_policy,
)
from investment_agent.repositories.personal import RepositoryUnavailable, VersionConflict

from ..auth import require_owner
from .common import WRITE_ERRORS, error, read_version, unavailable, write_error

router = APIRouter(prefix="/internal/universe")
COLLECTION, ACTIVE, INDEX = "approvals", "universe", "universe-proposal-index"
RequestId = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class ProposalRequest(ContractModel):
    proposal_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    as_of: date
    candidates: list[Candidate]
    request_id: str = RequestId


class DecisionRequest(ContractModel):
    request_id: str = RequestId


def _proposal_key(proposal_id):
    return f"universe-proposal-{proposal_id}"


def _active(repo, owner):
    record = read_version(repo, owner, COLLECTION, ACTIVE, None)
    return (UniverseVersion.model_validate(record.payload), record.version) if record else (None, 0)


def _closed():
    return error(409, "proposal_closed", "Đề xuất đã được xử lý.")


@router.get("")
def current(request: Request):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        active, version = _active(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    return {"version": version, "active": active.model_dump(mode="json") if active else None}


@router.get("/proposals")
def proposals(request: Request):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        index = read_version(repo, owner, COLLECTION, INDEX, None)
        rows = [read_version(repo, owner, COLLECTION, _proposal_key(pid), None) for pid in (index.payload["ids"] if index else [])]
    except RepositoryUnavailable:
        return unavailable()
    return {"proposals": [r.payload for r in rows if r is not None]}


@router.post("/proposals")
def propose(request: Request, body: ProposalRequest):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    # Evidence sent over the API is never trusted as a verified audit.
    candidates = [c.model_copy(update={"evidence": c.evidence.model_copy(update={"source": "caller_supplied"})}) for c in body.candidates]
    try:
        active, _ = _active(repo, owner)
        proposal = build_proposal(load_universe_policy(), body.proposal_id, candidates, active=active, as_of=body.as_of)
        repo.write(owner, COLLECTION, _proposal_key(body.proposal_id), {"proposal": proposal.model_dump(mode="json"), "decision": "pending"},
                   expected_version=0, request_id=body.request_id)
        index = read_version(repo, owner, COLLECTION, INDEX, None)
        ids = index.payload["ids"] if index else []
        if body.proposal_id not in ids:
            repo.write(owner, COLLECTION, INDEX, {"ids": [*ids, body.proposal_id]}, expected_version=index.version if index else 0,
                       request_id=f"{body.request_id}-index")
    except WRITE_ERRORS as exc:
        if isinstance(exc, VersionConflict):
            return error(409, "proposal_exists", "Mã đề xuất đã tồn tại.")
        return write_error(exc)
    return proposal.model_dump(mode="json")


def _decide(request: Request, proposal_id: str, body: DecisionRequest, decision: str):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    marker = f"{body.request_id}-decision"
    try:
        record = read_version(repo, owner, COLLECTION, _proposal_key(proposal_id), None)
        if record is None:
            return error(404, "proposal_missing", "Không tìm thấy đề xuất.")
        proposal = Proposal.model_validate(record.payload["proposal"])
        decided = record.version > 1
        if decided and (record.request_id != marker or record.payload["decision"] != decision):
            return _closed()
        result = {"proposal_id": proposal_id, "decision": decision}
        if decision == "approved":
            # Approve against the version the proposal was built on, so a retry rebuilds
            # the same payload; a newer active version makes the CAS write fail.
            base = read_version(repo, owner, COLLECTION, ACTIVE, proposal.base_version) if proposal.base_version else None
            try:
                new = approve(load_universe_policy(), proposal, active=UniverseVersion.model_validate(base.payload) if base else None,
                              actor="owner")
            except UniverseError as exc:
                return error(409, exc.code, "Đề xuất không còn phù hợp với danh sách hoặc chính sách hiện tại.")
            try:
                saved = repo.write(owner, COLLECTION, ACTIVE, new.model_dump(mode="json"), expected_version=proposal.base_version,
                                   request_id=body.request_id)
            except VersionConflict:
                return error(409, "proposal_outdated", "Danh sách đã thay đổi sau khi tạo đề xuất; hãy tạo đề xuất mới.")
            result = {"version": saved.version, "active": UniverseVersion.model_validate(saved.payload).model_dump(mode="json")}
        if not decided:
            repo.write(owner, COLLECTION, _proposal_key(proposal_id), {**record.payload, "decision": decision},
                       expected_version=1, request_id=marker)
    except VersionConflict:
        return _closed()
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return result


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(request: Request, proposal_id: str, body: DecisionRequest):
    return _decide(request, proposal_id, body, "approved")


@router.post("/proposals/{proposal_id}/reject")
def reject_proposal(request: Request, proposal_id: str, body: DecisionRequest):
    return _decide(request, proposal_id, body, "rejected")
