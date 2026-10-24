import time
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .auth import InternalAuthSettings, InternalAuthenticator, Unauthorized, require_owner
from .routes.health import router as health_router


def create_app(settings: InternalAuthSettings | None = None, *, clock: Callable[[], float] = time.time) -> FastAPI:
    authenticator = InternalAuthenticator(settings or InternalAuthSettings.from_env(), clock)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

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

    @app.get("/internal/identity")
    def identity(request: Request):
        owner = require_owner(request)
        return {"uid": owner.uid, "role": owner.role, "correlation_id": owner.correlation_id}

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="127.0.0.1", port=8000, workers=1, access_log=False, proxy_headers=False)
