"""Telegram settings and owner-initiated sending. The bot token lives in the server
environment only: it is never accepted, stored or returned here."""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.jobs.publication import get_report
from investment_agent.notifications.outbox import NotificationSettings, deliver
from investment_agent.notifications.render import render_report, split_message
from investment_agent.repositories.personal import RepositoryUnavailable

from ..auth import require_owner
from .common import WRITE_ERRORS, error, read_version, unavailable, write_error

router = APIRouter(prefix="/internal/notifications")
COLLECTION, RECORD = "settings", "notifications"
DISABLED = NotificationSettings(enabled=False, members_may_view_personal_data=False, scheduled_enabled=False)


class SettingsRequest(ContractModel):
    settings: NotificationSettings
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class ReportRequest(ContractModel):
    report_id: str = Field(pattern=r"^[a-f0-9]{32}$")


class SendRequest(ReportRequest):
    confirm: bool


class ResolveRequest(ReportRequest):
    part: int = Field(strict=True, ge=0)
    outcome: Literal["received", "not_received"]


def current_settings(repo, owner) -> tuple[NotificationSettings, int]:
    record = read_version(repo, owner, COLLECTION, RECORD, None)
    return (NotificationSettings.model_validate(record.payload), record.version) if record else (DISABLED, 0)


def _deps(request):
    owner = require_owner(request)
    return owner, request.app.state.personal_repository, request.app.state


@router.get("/settings")
def get_settings(request: Request):
    owner, repo, state = _deps(request)
    if repo is None:
        return unavailable()
    try:
        settings, version = current_settings(repo, owner)
    except RepositoryUnavailable:
        return unavailable()
    return {"version": version, "settings": settings.model_dump(mode="json"), "bot_token_configured": state.telegram is not None}


@router.put("/settings")
def put_settings(request: Request, body: SettingsRequest):
    owner, repo, _ = _deps(request)
    if repo is None:
        return unavailable()
    try:
        record = repo.write(owner, COLLECTION, RECORD, body.settings.model_dump(mode="json"), expected_version=body.expected_version,
                            request_id=body.request_id)
    except WRITE_ERRORS as exc:
        return write_error(exc)
    return {"version": record.version, "settings": record.payload}


def _report(repo, owner, report_id):
    return get_report(repo, owner, report_id)


@router.post("/preview")
def preview(request: Request, body: ReportRequest):
    owner, repo, _ = _deps(request)
    if repo is None:
        return unavailable()
    report = _report(repo, owner, body.report_id)
    if report is None:
        return error(404, "report_missing", "Không tìm thấy bản tin.")
    return {"parts": split_message(render_report(report)), "status": report["status"]}


@router.post("/test-send")
def test_send(request: Request, body: SendRequest):
    """Real send to the configured group, only on an explicit owner action."""
    owner, repo, state = _deps(request)
    if state.telegram is None or state.deliveries is None:
        return error(503, "telegram_not_configured", "Chưa cấu hình Bot Token phía máy chủ.")
    if repo is None:
        return unavailable()
    if not body.confirm:
        return error(422, "confirmation_required", "Cần xác nhận gửi thật tới nhóm đã cấu hình.")
    settings, _ = current_settings(repo, owner)
    report = _report(repo, owner, body.report_id)
    if report is None:
        return error(404, "report_missing", "Không tìm thấy bản tin.")
    result = deliver(report, settings, state.telegram, state.deliveries)
    return {"status": result.status, "parts_sent": result.parts_sent, "parts_total": result.parts_total}


@router.get("/deliveries/{report_id}")
def deliveries(request: Request, report_id: str):
    owner, repo, state = _deps(request)
    if state.deliveries is None or repo is None:
        return unavailable()
    settings, _ = current_settings(repo, owner)
    report = _report(repo, owner, report_id) if len(report_id) == 32 else None
    version = report.get("report_version", "1") if report else "1"
    parts = state.deliveries.parts(report_id, settings.chat_id, version) if settings.chat_id else []
    return {"parts": [{"index": p.index, "count": p.count, "status": p.status, "message_id": p.message_id} for p in parts]}


@router.post("/resolve")
def resolve(request: Request, body: ResolveRequest):
    owner, repo, state = _deps(request)
    if state.deliveries is None or repo is None:
        return unavailable()
    settings, _ = current_settings(repo, owner)
    report = _report(repo, owner, body.report_id)
    if report is None or not settings.chat_id:
        return error(404, "report_missing", "Không tìm thấy bản tin hoặc nhóm nhận.")
    state.deliveries.resolve_unknown(body.report_id, settings.chat_id, body.part, outcome=body.outcome, version=report.get("report_version", "1"))
    return {"status": "resolved"}
