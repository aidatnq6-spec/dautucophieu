"""Quy trình đầu tư on Nhật ký: the owner's cards on five columns, checked against the ledger and the open theses."""

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.idea_board import BoardError, board_view, merge_cards
from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.records import read_version
from investment_agent.services.theses import read_theses

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error
from .watchlist import held_tickers

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
RECORD = ("settings", "idea_board")


class BoardRequest(ContractModel):
    cards: list[dict] = Field(max_length=80)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    record = read_version(repo, owner, *RECORD, None)
    theses = {t["symbol"] for t in read_theses(repo, owner)[0] if t["closed_on"] is None}
    view = board_view((record.payload if record else {}).get("cards", []), held=held_tickers(request), theses=theses,
                      today=now(request).astimezone(VN).date())
    return {"version": record.version if record else 0, **view}


@router.get("/journal/board")
def get_board(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/journal/board")
def put_board(request: Request, body: BoardRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        stored = read_version(repo, owner, *RECORD, None)
        cards = merge_cards((stored.payload if stored else {}).get("cards", []), body.cards, today=now(request).astimezone(VN).date())
        repo.write(owner, *RECORD, {"cards": cards}, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except BoardError as exc:
        return error(422, exc.code, exc.message)
    except WRITE_ERRORS as exc:
        return write_error(exc)
