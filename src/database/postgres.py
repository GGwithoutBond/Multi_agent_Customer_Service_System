"""
PostgreSQL 数据库连接管理
基于 SQLAlchemy 2.0 异步引擎
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

_engine: Optional[AsyncEngine] = None


def get_engine() -> AsyncEngine:
    """获取数据库引擎单例"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _engine


async def init_postgres() -> None:
    """初始化 PostgreSQL 连接池"""
    engine = get_engine()
    # 测试连接
    async with engine.connect() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("SELECT 1")
        )
    logger.info("PostgreSQL 连接池已创建: %s", get_settings().POSTGRES_HOST)


async def close_postgres() -> None:
    """关闭 PostgreSQL 连接池"""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        logger.info("PostgreSQL 连接池已关闭")
