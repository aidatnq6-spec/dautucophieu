from datetime import date, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from investment_agent.domain.models import ContractModel
from investment_agent.jobs.daily import run_after_close
from investment_agent.jobs.runner import LeaseBusy

from ..auth import require_owner
from .common import error, now as request_now, unavailable

router = APIRouter(prefix="/internal/jobs")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class AfterCloseRequest(ContractModel):
    session_date: date


@router.post("/after-close")
def after_close(request: Request, body: AfterCloseRequest, background: BackgroundTasks):
    owner = require_owner(request)
    state = request.app.state
    if state.personal_repository is None or state.jobs is None or state.outbox is None:
        return unavailable()
    now = request_now(request)
    if body.session_date > now.astimezone(VN).date():
        return error(422, "session_in_future", "Phiên chưa diễn ra.")
    accepted = uuid4().hex
    results = state.accepted_jobs
    results[accepted] = ""  # observable as "accepted" before the background work starts

    def work():
        try:
            outcome = run_after_close(repo=state.personal_repository, owner=owner, market=state.market, jobs=state.jobs, outbox=state.outbox,
                                      session_date=body.session_date, now=now, worker_id=f"api-{accepted}")
            results[accepted] = outcome.job_id
        except LeaseBusy:
            results[accepted] = None
    background.add_task(work)
    # Closing the browser does not cancel the computation; the UI only stops observing it.
    return JSONResponse({"job_id": accepted, "status": "accepted"}, status_code=202)


@router.get("/{job_id}")
def job_status(request: Request, job_id: str):
    require_owner(request)
    state = request.app.state
    if state.jobs is None:
        return unavailable()
    accepted = state.accepted_jobs
    if job_id in accepted and accepted[job_id] is None:
        return {"job_id": job_id, "status": "busy", "report_id": None, "stages": []}
    if accepted.get(job_id) == "":
        return {"job_id": job_id, "status": "accepted", "report_id": None, "stages": []}
    record = state.jobs.get(accepted.get(job_id, job_id))
    if record is None:
        return {"job_id": job_id, "status": "accepted", "report_id": None, "stages": []} if job_id in accepted else \
            error(404, "job_missing", "Không tìm thấy tác vụ.")
    return {"job_id": job_id, "status": record["status"], "report_id": record["report_id"], "stages": record["stages"], "reason": record["reason"]}
