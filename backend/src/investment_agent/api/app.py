import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from investment_agent.market.view import EmptyMarket

from .auth import InternalAuthSettings, InternalAuthenticator, Unauthorized, require_owner
from .routes.health import router as health_router
from .routes.profile import router as profile_router
from .routes.ledger import router as ledger_router
from .routes.jobs import router as jobs_router
from .routes.overview import router as overview_router
from .routes.reports import router as reports_router
from .routes.risk import router as risk_router
from .routes.universe import router as universe_router
from .routes.valuation_assumptions import router as valuation_router


def create_app(settings: InternalAuthSettings | None = None, *, clock: Callable[[], float] = time.time, personal_repository=None,
               market=None, jobs=None, outbox=None) -> FastAPI:
    """personal_repository None keeps personal routes fail-closed (503)."""
    authenticator = InternalAuthenticator(settings or InternalAuthSettings.from_env(), clock)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.clock, app.state.personal_repository = clock, personal_repository
    app.state.market = market or EmptyMarket()  # no licensed market source is connected yet
    app.state.jobs, app.state.outbox = jobs, outbox  # both required for report jobs
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

    @app.get("/internal/identity")
    def identity(request: Request):
        owner = require_owner(request)
        return {"uid": owner.uid, "role": owner.role, "correlation_id": owner.correlation_id}

    return app


if __name__ == "__main__":
    import uvicorn
    from investment_agent.repositories.firestore import personal_repository_from_env
    from investment_agent.repositories.personal import RepositoryUnavailable
    try:
        repository = personal_repository_from_env()
    except RepositoryUnavailable:
        repository = None  # Personal routes answer 503 until Firebase Admin is configured.
    uvicorn.run(create_app(personal_repository=repository), host="127.0.0.1", port=8000, workers=1, access_log=False, proxy_headers=False)
