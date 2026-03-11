"""
应用生命周期事件
管理 FastAPI 启动和关闭时的资源初始化与清理
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from src.core.config import get_settings
from src.core.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI 生命周期管理"""
    settings = get_settings()

    # ── 启动阶段 ──
    setup_logging(log_level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)
    logger.info("🚀 正在启动 %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    # 初始化数据库连接池
    from src.database.postgres import init_postgres, close_postgres
    from src.database.redis import init_redis, close_redis

    await init_postgres()
    logger.info("✅ PostgreSQL 连接池已初始化")

    await init_redis()
    logger.info("✅ Redis 连接已初始化")

    logger.info("🎉 应用启动完成")

    yield

    # ── 关闭阶段 ──
    logger.info("正在关闭应用...")

    await close_redis()
    logger.info("Redis 连接已关闭")

    await close_postgres()
    logger.info("PostgreSQL 连接池已关闭")

    logger.info("👋 应用已安全关闭")
