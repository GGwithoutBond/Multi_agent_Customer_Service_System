"""
FastAPI 应用入口
多智能体客服系统 - 主程序入口
"""

import os

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.middlewares import setup_exception_handlers, setup_middlewares
from src.api.v1.router import api_v1_router
from src.core.config import get_settings
from src.core.events import lifespan


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="基于 Orchestrator-Worker 架构的多智能体客服系统",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # 配置中间件
    setup_middlewares(app)

    # 配置异常处理
    setup_exception_handlers(app)

    # 注册路由
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # 挂载上传文件的静态访问
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
