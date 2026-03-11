"""
API 中间件
包含请求日志、CORS、限流等中间件
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


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 记录请求
        logger.info(
            "→ %s %s",
            request.method,
            request.url.path,
        )

        response = await call_next(request)

        # 记录响应
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "← %s %s [%d] %dms",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )

        # 添加响应头
        response.headers["X-Response-Time"] = f"{latency_ms}ms"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    优化 6.3: 简易 IP 限流中间件
    基于滑动时间窗口的内存限流
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._request_counts: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过静态文件和健康检查
        path = request.url.path
        if path.startswith("/uploads") or path in ("/", "/docs", "/redoc", "/openapi.json", "/health"):
            return await call_next(request)

        # 获取客户端 IP
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # 清理过期记录（60 秒前的）
        self._request_counts[client_ip] = [
            t for t in self._request_counts[client_ip]
            if now - t < 60
        ]

        # 检查限流
        if len(self._request_counts[client_ip]) >= self.requests_per_minute:
            logger.warning("🚫 限流触发: IP=%s, 请求数=%d/min", client_ip, len(self._request_counts[client_ip]))
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "请求过于频繁，请稍后再试",
                    "detail": f"限制: {self.requests_per_minute} 次/分钟",
                },
                headers={"Retry-After": "60"},
            )

        # 记录请求
        self._request_counts[client_ip].append(now)

        # 定期清理（防止内存泄漏）
        if len(self._request_counts) > 10000:
            old_ips = [
                ip for ip, times in self._request_counts.items()
                if not times or now - times[-1] > 300
            ]
            for ip in old_ips:
                del self._request_counts[ip]

        response = await call_next(request)

        # 添加限流信息到响应头
        remaining = self.requests_per_minute - len(self._request_counts[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(remaining, 0))

        return response


def setup_middlewares(app: FastAPI) -> None:
    """配置所有中间件"""
    settings = get_settings()

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 优化 6.3: 限流中间件
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.API_RATE_LIMIT,
    )

    # 请求日志中间件
    app.add_middleware(RequestLoggingMiddleware)


def setup_exception_handlers(app: FastAPI) -> None:
    """配置全局异常处理"""

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
        logger.error("未处理的异常: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "服务内部错误",
                "detail": str(exc) if get_settings().DEBUG else None,
            },
        )
