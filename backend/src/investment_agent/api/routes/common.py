"""Shared responses for personal routes: Vietnamese messages, no personal payload echo."""

from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse

from investment_agent.repositories.personal import IdempotencyConflict, RepositoryUnavailable, VersionConflict
from investment_agent.services.records import read_current, read_version  # noqa: F401 (re-exported for routes)


def error(status, code, message):
    return JSONResponse({"code": code, "message": message}, status_code=status)


def unavailable():
    return error(503, "personal_repository_unavailable", "Chưa kết nối được kho dữ liệu cá nhân; không ghi thay đổi.")


def now(request: Request) -> datetime:
    return datetime.fromtimestamp(request.app.state.clock(), timezone.utc)


def committed_retry(repo, owner, collection, record_id, expected_version, request_id):
    """The revision a request already committed, when a retry's payload differs only by a server timestamp."""
    record = read_version(repo, owner, collection, record_id, expected_version + 1)
    return record if record is not None and record.request_id == request_id else None


def write_error(exc):
    if isinstance(exc, VersionConflict):
        return error(409, "version_conflict", "Dữ liệu đã được cập nhật ở nơi khác; hãy tải lại.")
    if isinstance(exc, IdempotencyConflict):
        return error(409, "request_reused", "Mã yêu cầu đã dùng cho nội dung khác.")
    if isinstance(exc, RepositoryUnavailable):
        return unavailable()
    raise exc


WRITE_ERRORS = (VersionConflict, IdempotencyConflict, RepositoryUnavailable)
