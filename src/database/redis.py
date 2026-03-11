"""
Redis 连接管理
提供异步 Redis 客户端的初始化、获取和关闭
"""

from typing import Optional

from redis.asyncio import Redis

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """初始化 Redis 连接"""
    global _redis_client
    settings = get_settings()
    _redis_client = Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=20,
    )
    # 测试连接
    await _redis_client.ping()
    logger.info("Redis 连接已建立: %s:%s", settings.REDIS_HOST, settings.REDIS_PORT)


def get_redis() -> Redis:
    """获取 Redis 客户端"""
    if _redis_client is None:
        raise RuntimeError("Redis 尚未初始化，请先调用 init_redis()")
    return _redis_client


async def close_redis() -> None:
    """关闭 Redis 连接"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis 连接已关闭")
