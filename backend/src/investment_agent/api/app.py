import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from investment_agent.market.view import EmptyMarket

from .auth import InternalAuthSettings, InternalAuthenticator, Unauthorized, require_owner
from .routes.fairvalue import router as fairvalue_router
from .routes.health import router as health_router
from .routes.profile import router as profile_router
from .routes.ledger import router as ledger_router
from .routes.macro import router as macro_router
from .routes.trend import router as trend_router
from .routes.notifications import router as notifications_router
from .routes.jobs import router as jobs_router
from .routes.overview import router as overview_router
from .routes.reports import router as reports_router
from .routes.risk import router as risk_router
from .routes.settings import router as settings_router
from .routes.universe import router as universe_router
from .routes.valuation_assumptions import router as valuation_router
from .routes.watchlist import router as watchlist_router


def create_app(settings: InternalAuthSettings | None = None, *, clock: Callable[[], float] = time.time, personal_repository=None,
               market=None, jobs=None, outbox=None, telegram=None, deliveries=None, data_dir=None) -> FastAPI:
    """personal_repository None keeps personal routes fail-closed (503)."""
    authenticator = InternalAuthenticator(settings or InternalAuthSettings.from_env(), clock)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.clock, app.state.personal_repository = clock, personal_repository
    app.state.market = market or EmptyMarket()  # no licensed market source is connected yet
    app.state.jobs, app.state.outbox = jobs, outbox  # both required for report jobs
    app.state.telegram, app.state.deliveries = telegram, deliveries  # sender holds the bot token; None = not configured
    app.state.data_dir = data_dir  # market-symbols.txt and index-groups.json for the watchlist
    app.state.accepted_jobs = {}  # accepted request id -> job id (None when another worker held the lease)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, exc: RequestValidationError):
        # Field locations only: validation details echo submitted personal amounts.
        fields = sorted({".".join(str(part) for part in error["loc"][1:]) for error in exc.errors()})
        return JSONResponse({"code": "invalid_request", "message": "Dữ liệu gửi lên không hợp lệ.", "fields": fields}, status_code=422)

    @app.middleware("http")
    async def authenticated_boundary(request: Request, call_next):
        try:
            if request.url.path != "/health" or request.method != "GET":
                body = await request.body()
                if len(body) > 1_048_576:
                    return JSONResponse({"code": "request_too_large", "message": "Yêu cầu quá lớn."}, status_code=413, headers={"Cache-Control": "no-store"})
                request.state.owner = authenticator.verify(request, body)
            response = await call_next(request)
        except Unauthorized:
            response = JSONResponse({"code": "unauthorized", "message": "Yêu cầu nội bộ không hợp lệ."}, status_code=401)
        response.headers["Cache-Control"] = "no-store"
        return response

    app.include_router(health_router)
    app.include_router(profile_router)
    app.include_router(risk_router)
    app.include_router(ledger_router)
    app.include_router(universe_router)
    app.include_router(valuation_router)
    app.include_router(overview_router)
    app.include_router(jobs_router)
    app.include_router(reports_router)
    app.include_router(notifications_router)
    app.include_router(settings_router)
    app.include_router(watchlist_router)
    app.include_router(macro_router)
    app.include_router(trend_router)
    app.include_router(fairvalue_router)

    @app.get("/internal/identity")
    def identity(request: Request):
        owner = require_owner(request)
        return {"uid": owner.uid, "role": owner.role, "correlation_id": owner.correlation_id}

    return app


if __name__ == "__main__":
    import os
    from pathlib import Path

    import httpx
    import uvicorn

    from investment_agent.jobs.runner import JobStore
    from investment_agent.notifications.outbox import DeliveryStore
    from investment_agent.notifications.telegram import TelegramSender
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.repositories.personal import RepositoryUnavailable
    from investment_agent.settings import Settings

    try:
        repository = personal_repository_from_env()
    except RepositoryUnavailable:
        repository = None  # Personal routes answer 503 until Firebase Admin is configured.
    data_dir = Path(os.environ.get("INVESTMENT_DATA_DIR", "data")).resolve()
    from datetime import datetime

    from investment_agent.cli import load_calendar
    from investment_agent.market.prices import PriceStore
    from investment_agent.market.view import StoreMarket
    from zoneinfo import ZoneInfo

    from investment_agent.domain.pinned import CONFIG_DIR
    hanoi_today = lambda: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()  # noqa: E731
    calendar_path = CONFIG_DIR / f"trading-calendar-hose-{hanoi_today().year}.json"
    market = None  # EmptyMarket unless prices were synced and this year's calendar exists
    if (data_dir / "prices").exists() and calendar_path.exists():
        market = StoreMarket(PriceStore(data_dir), load_calendar(calendar_path), today=hanoi_today)
    deliveries = DeliveryStore(data_dir / "deliveries.sqlite")  # also the report outbox
    token = Settings.from_env().telegram_bot_token
    uvicorn.run(create_app(personal_repository=repository, market=market, jobs=JobStore(data_dir / "jobs.sqlite"), outbox=deliveries,
                           deliveries=deliveries, data_dir=data_dir,
                           telegram=TelegramSender(token, client=httpx.Client()) if token else None),
                host="127.0.0.1", port=8000, workers=1, access_log=False, proxy_headers=False)
