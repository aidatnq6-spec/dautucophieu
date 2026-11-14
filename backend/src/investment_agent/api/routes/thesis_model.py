"""Kịch bản và chỉ báo on a watched ticker's page (L1, L3)."""

import re
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from pydantic import Field

from investment_agent.domain.models import ContractModel
from investment_agent.domain.thesis_model import ModelError, validate_model
from investment_agent.market.watchlist import load_watchlist
from investment_agent.repositories.personal import RepositoryUnavailable
from investment_agent.services.thesis_model import RECORD, read_models, view_for

from ..auth import require_owner
from .common import WRITE_ERRORS, error, now, unavailable, write_error

router = APIRouter(prefix="/internal")
VN = ZoneInfo("Asia/Ho_Chi_Minh")
_SYMBOL = re.compile(r"^[A-Z0-9]{3,10}$")
EMPTY = {"scenarios": [], "review": {"when": "", "on": None}, "indicators": []}


class ModelRequest(ContractModel):
    scenarios: list[dict] = Field(max_length=3)
    review: dict | None = None
    indicators: list[dict] = Field(max_length=15)
    expected_version: int = Field(strict=True, ge=0)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")


def _watched(request: Request, symbol: str) -> str | None:
    data_dir = request.app.state.data_dir
    symbol = symbol.upper()
    return symbol if data_dir is not None and _SYMBOL.fullmatch(symbol) and symbol in load_watchlist(Path(data_dir)).symbols else None


def _view(request: Request, symbol: str, models: dict, version: int) -> dict:
    model = models.get(symbol) or EMPTY
    return {"symbol": symbol, "version": version, "model": model,
            **view_for(request.app.state.data_dir, symbol, model, today=now(request).astimezone(VN).date())}


@router.get("/stock/{symbol}/model")
def get_model(symbol: str, request: Request):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    try:
        return _view(request, sym, *read_models(repo, owner))
    except RepositoryUnavailable:
        return unavailable()


@router.put("/stock/{symbol}/model")
def put_model(symbol: str, request: Request, body: ModelRequest):
    owner, repo = require_owner(request), request.app.state.personal_repository
    if repo is None:
        return unavailable()
    if not (sym := _watched(request, symbol)):
        return error(404, "symbol_not_watched", "Mã này không có trong danh sách theo dõi.")
    try:
        model = validate_model({"scenarios": body.scenarios, "review": body.review, "indicators": body.indicators})
        models, _ = read_models(repo, owner)
        models = {**models, sym: model} if (model["scenarios"] or model["indicators"] or model["review"]["when"]) else {k: v for k, v in models.items() if k != sym}
        record = repo.write(owner, *RECORD, {"models": models}, expected_version=body.expected_version, request_id=body.request_id)
        return _view(request, sym, models, record.version)
    except ModelError as exc:
        return error(422, exc.code, exc.message)
    except WRITE_ERRORS as exc:
        return write_error(exc)
