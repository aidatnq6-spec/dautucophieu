from fastapi import APIRouter, Request

from investment_agent.jobs.publication import get_report, list_reports
from investment_agent.repositories.personal import InvalidRecord, RepositoryUnavailable

from ..auth import require_owner
from .common import error, unavailable

router = APIRouter(prefix="/internal/reports")


@router.get("")
def reports(request: Request):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return {"reports": list(reversed(list_reports(repo, owner)))}
    except RepositoryUnavailable:
        return unavailable()


@router.get("/{report_id}")
def report(request: Request, report_id: str):
    owner = require_owner(request)
    repo = request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        found = get_report(repo, owner, report_id)
    except InvalidRecord:
        found = None
    except RepositoryUnavailable:
        return unavailable()
    if not found:
        return error(404, "report_missing", "Không tìm thấy bản tin.")
    from investment_agent.brief.view import market_for_session

    from .watchlist import held_tickers
    try:
        held = held_tickers(request)
    except RepositoryUnavailable:
        held = set()
    # The Firestore record stays write-once; the public market section is read from data/brief by session date.
    return {**found, "market": market_for_session(request.app.state.data_dir, held)(found.get("session_date"))}
