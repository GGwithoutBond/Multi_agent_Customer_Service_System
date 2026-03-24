"""
API middlewares and exception handlers.
"""

import time
from collections import defaultdict
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import get_settings
from src.core.exceptions import BaseAppException
from src.core.logging import get_logger

logger = get_logger(__name__)

_HEALTH_PATHS = {
    "/health",
    "/api/v1/health",
    "/api/v1/admin/health",
}

_PUBLIC_PATHS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def _should_skip_rate_limit(path: str) -> bool:
    if path.startswith("/uploads"):
        return True
    if path in _PUBLIC_PATHS:
        return True
    if path in _HEALTH_PATHS:
        return True
    return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request and response metadata."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        logger.info("request start method=%s path=%s", request.method, request.url.path)

        response = await call_next(request)

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "request end method=%s path=%s status=%s latency_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )
        response.headers["X-Response-Time"] = f"{latency_ms}ms"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window IP rate limiter."""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._request_counts: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if _should_skip_rate_limit(path):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        self._request_counts[client_ip] = [
            t for t in self._request_counts[client_ip] if now - t < 60
        ]

        if len(self._request_counts[client_ip]) >= self.requests_per_minute:
            logger.warning(
                "rate limited ip=%s path=%s requests=%s",
                client_ip,
                path,
                len(self._request_counts[client_ip]),
            )
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "请求过于频繁，请稍后重试",
                    "detail": f"限制: {self.requests_per_minute} 次/分钟",
                },
                headers={"Retry-After": "60"},
            )

        self._request_counts[client_ip].append(now)

        if len(self._request_counts) > 10000:
            old_ips = [
                ip for ip, times in self._request_counts.items() if not times or now - times[-1] > 300
            ]
            for ip in old_ips:
                del self._request_counts[ip]

        response = await call_next(request)

        remaining = self.requests_per_minute - len(self._request_counts[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(remaining, 0))
        return response


def setup_middlewares(app: FastAPI) -> None:
    """Configure all middlewares."""

    settings = get_settings()
    origins = [origin.strip() for origin in (settings.ALLOWED_ORIGINS or []) if origin.strip()]

    if settings.ENVIRONMENT.lower() == "production" and "*" in origins:
        origins = [origin for origin in origins if origin != "*"]
        logger.warning("Removed wildcard CORS origin in production for security hardening.")

    if not origins:
        origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    allow_credentials = "*" not in origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.API_RATE_LIMIT,
    )
    app.add_middleware(RequestLoggingMiddleware)


def setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""

    @app.exception_handler(BaseAppException)
    async def app_exception_handler(request: Request, exc: BaseAppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务内部错误",
                "detail": str(exc) if get_settings().DEBUG else None,
            },
        )
