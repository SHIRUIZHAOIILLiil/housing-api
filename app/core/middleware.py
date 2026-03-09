import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request


logger = logging.getLogger("housing_api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.perf_counter()

        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        client_ip = request.client.host if request.client else "unknown"
        request.state.request_id = request_id
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            logger.info(
                "request_id=%s ip=%s method=%s path=%s query=%s status=%s duration_ms=%s",
                request_id,
                client_ip,
                method,
                path,
                query,
                response.status_code,
                duration_ms,
            )

            response.headers["X-Request-ID"] = request_id
            return response

        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            logger.exception(
                "request_id=%s ip=%s method=%s path=%s query=%s status=500 duration_ms=%s",
                request_id,
                client_ip,
                method,
                path,
                query,
                duration_ms,
            )
            raise