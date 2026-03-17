"""Request logging middleware — assigns a UUID request_id and logs every request."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware

from backend.utils.logger import get_logger

if TYPE_CHECKING:
    from fastapi import Request, Response
    from starlette.middleware.base import RequestResponseEndpoint

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Attach ``request_id`` to every request and emit structured access logs."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        # Bind request_id so all downstream logs include it automatically.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Attempt to extract user_id from an already-decoded auth state.
        user_id: str | None = getattr(request.state, "user_id", None)
        if user_id:
            structlog.contextvars.bind_contextvars(user_id=user_id)

        response: Response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            request_id=request_id,
        )

        return response
