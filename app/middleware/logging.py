"""Structured request/response logging middleware."""

from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

log = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Emit a JSON log line for every HTTP request.

    Each line includes: method, path, status_code, duration_ms, request_id.
    The request_id is propagated in the response header X-Request-ID.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            log.error(
                "request.error",
                method=request.method,
                path=request.url.path,
                error=str(exc),
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log.info(
            "request.completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
