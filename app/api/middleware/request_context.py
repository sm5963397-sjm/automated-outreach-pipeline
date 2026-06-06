from __future__ import annotations

import time
import uuid
from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, request_id_ctx

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        response: Response | None = None
        try:
            response = cast(Response, await call_next(request))
            return response
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            status_code = response.status_code if response is not None else 500
            logger.info(
                "http_request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "elapsed_ms": elapsed_ms,
                },
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            request_id_ctx.reset(token)
