import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.monotonic()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            tenant_slug = request.path_params.get("tenant_slug") if hasattr(request, "path_params") else None
            logging.getLogger("app.request").info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%s tenant_slug=%s",
                request_id,
                request.method,
                request.url.path,
                getattr(response, "status_code", 500),
                duration_ms,
                tenant_slug or "-",
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
