"""Kế hoạch tích sản on Hồ sơ & rủi ro. A purchase recorded here changes Sổ tài sản (and so Tháp tài sản) only when the owner adds it there, one at a time."""

from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.accumulation import Accumulation, PostRefused, post_to_book
from investment_agent.domain.models import ContractModel
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.accumulation import RECORD, accumulation_view, read_data
from investment_agent.services.deposit_book import RECORD as BOOK_RECORD, book_quotes, read_book

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")


class AccumulationRequest(Accumulation):
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


class PostRequest(ContractModel):
    buy: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    row: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,64}$")  # None: a new row
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _view(request: Request, repo, owner) -> dict:
    return accumulation_view(repo, owner, quotes=book_quotes(request.app.state.data_dir), today=now(request).astimezone(VN).date())


@router.get("/accumulation")
def get_accumulation(request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    try:
        return _view(request, repo, owner)
    except RepositoryUnavailable:
        return unavailable()


@router.put("/accumulation")
def put_accumulation(request: Request, body: AccumulationRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    payload = Accumulation.model_validate(body.model_dump(exclude={"expected_version", "request_id"})).model_dump(mode="json")
    try:
        repo.write(owner, *RECORD, payload, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)


@router.post("/accumulation/post")
def post_buy(request: Request, body: PostRequest):
    """One purchase into Sổ tài sản, and its mark, in one transaction: a purchase can never be in the book without the mark, or added twice."""
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None or request.app.state.data_dir is None:
        return unavailable()
    try:
        data, version = read_data(repo, owner)
        buy = next((b for b in data.buys if b.id == body.buy), None)
        if buy is None:
            return error(404, "unknown_buy", "Không tìm thấy lần mua này.")
        if version != body.expected_version:
            return error(409, "version_conflict", "Dữ liệu đã được cập nhật ở nơi khác; hãy tải lại.")
        if buy.book_row is not None:
            return error(409, "already_posted", "Lần mua này đã được cộng vào Sổ tài sản.")
        book, book_version = read_book(repo, owner)
        if book is None:  # saving a first, nearly empty book would turn every layer of Tháp tài sản to it
            return error(422, "no_book", "Sổ tài sản chưa có dữ liệu; hãy nhập Sổ tài sản trước.")
        plan = next(p for p in data.plans if p.id == buy.plan)
        try:
            new_book, row = post_to_book(book, plan, buy, body.row, new_id=uuid4().hex)
        except PostRefused as exc:
            return error(422, "cannot_post", str(exc))
        marked = data.model_copy(update={"buys": tuple(b.model_copy(update={"book_row": row}) if b.id == buy.id else b for b in data.buys)})
        repo.write_many(owner, [(*BOOK_RECORD, new_book.model_dump(mode="json"), book_version), (*RECORD, marked.model_dump(mode="json"), version)], request_id=body.request_id)
        return _view(request, repo, owner)
    except WRITE_ERRORS as exc:
        return write_error(exc)
