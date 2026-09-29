"""
Request correlation and logging middleware.
Ensures every incoming HTTP request receives or forwards a unique X-Request-ID.
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("udyamsetu.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches a unique request_id to request.state and response headers,
    and logs request timing metrics.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Inject tracing header in response
        response.headers["X-Request-ID"] = request_id

        logger.info(
            f"{request.method} {request.url.path} "
            f"Status:{response.status_code} ({duration_ms:.2f}ms) "
            f"req_id={request_id}"
        )
        return response
