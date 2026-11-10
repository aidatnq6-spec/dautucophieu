"""Thu chi hằng tháng on Hồ sơ & rủi ro: the owner uploads their spending workbook; a preview writes nothing, saving keeps the monthly totals only."""

import base64
import binascii
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.cashflow_workbook import CashflowFileError, parse_cashflow_xlsx
from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.cashflow import RECORD, cashflow_view, merge_import
from investment_agent.services.records import read_version

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
MAX_FILE = 6 * 1024 * 1024  # workbooks with pictures run to a few MB
WEALTH = ("settings", "wealth_check")


class ImportRequest(ContractModel):
    content_base64: str = Field(max_length=8_400_000)
    commit: bool = False
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    stored = read_version(repo, owner, *RECORD, None)
    wealth = read_version(repo, owner, *WEALTH, None)
    birth = wealth.payload.get("birth_year") if wealth else None
    return {"version": stored.version if stored else 0, **cashflow_view(stored.payload if stored else None, today=now(request).astimezone(VN).date(), birth_year=birth)}


@router.get("/cashflow")
def get_cashflow(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.post("/cashflow/import")
def import_cashflow(request: Request, body: ImportRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    try:
        data = base64.b64decode(body.content_base64, validate=True)
    except (binascii.Error, ValueError):
        return error(422, "invalid_file", "Không đọc được file đã gửi.")
    if len(data) > MAX_FILE:
        return error(422, "invalid_file", "File lớn hơn 6 MB.")
    try:
        parsed = parse_cashflow_xlsx(data)
    except CashflowFileError as exc:
        return error(422, "invalid_file", str(exc))
    preview = {"year": parsed["year"], "months": sorted(parsed["months"]), "warnings": parsed["warnings"], "sources": parsed["sources"]}
    try:
        if not body.commit:
            return {**_view(request, repo, owner), "preview": preview}
        stored = read_version(repo, owner, *RECORD, None)
        if (stored.version if stored else 0) != body.expected_version:
            return error(409, "version_conflict", "Dữ liệu đã được cập nhật ở nơi khác; hãy tải lại.")
        payload = merge_import(stored.payload if stored else {}, parsed, imported_at=now(request).astimezone(VN).isoformat(timespec="seconds"))
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return {**_view(request, repo, owner), "preview": preview}
    except RepositoryUnavailable:
        return unavailable()
    except WRITE_ERRORS as exc:
        return write_error(exc)
