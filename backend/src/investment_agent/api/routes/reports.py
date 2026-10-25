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
    return found if found else error(404, "report_missing", "Không tìm thấy bản tin.")
