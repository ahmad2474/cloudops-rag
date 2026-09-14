"""RFC 7807 problem responses for library errors and unexpected failures."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cloudops_rag.errors import CloudOpsRagError, RateLimitedError
from cloudops_rag.logging import get_logger

log = get_logger("api.errors")


def _problem(request: Request, status: int, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
            "request_id": getattr(request.state, "request_id", None),
        },
        media_type="application/problem+json",
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RateLimitedError)
    async def _rate_limited(request: Request, exc: RateLimitedError) -> JSONResponse:
        resp = _problem(request, exc.status_code, exc.title, str(exc))
        resp.headers["Retry-After"] = str(max(1, int(exc.retry_after + 0.999)))
        return resp

    @app.exception_handler(CloudOpsRagError)
    async def _domain(request: Request, exc: CloudOpsRagError) -> JSONResponse:
        log.warning("domain_error", error=type(exc).__name__, detail=str(exc))
        return _problem(request, exc.status_code, exc.title, str(exc))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_error", error=type(exc).__name__)
        return _problem(request, 500, "Internal error", "unexpected error; see request_id")
