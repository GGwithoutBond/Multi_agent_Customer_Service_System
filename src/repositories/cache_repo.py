"""
缓存数据访问层 (Redis)
提供通用的缓存读写操作
"""

import json
from typing import Any, Optional

from src.core.logging import get_logger
from src.database.redis import get_redis

logger = get_logger(__name__)


class CacheRepository:
    """Redis 缓存 Repository"""

    def __init__(self, prefix: str = "agent"):
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[str]:
        """获取缓存值"""
        redis = get_redis()
        return await redis.get(self._key(key))

    async def get_json(self, key: str) -> Optional[Any]:
        """获取 JSON 缓存值"""
        value = await self.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(
        self, key: str, value: str, expire: Optional[int] = None
    ) -> None:
        """设置缓存值"""
        redis = get_redis()
        await redis.set(self._key(key), value, ex=expire)

    async def set_json(
        self, key: str, value: Any, expire: Optional[int] = None
    ) -> None:
        """设置 JSON 缓存值"""
        await self.set(key, json.dumps(value, ensure_ascii=False, default=str), expire)

    async def delete(self, key: str) -> None:
        """删除缓存"""
        redis = get_redis()
        await redis.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        """判断缓存是否存在"""
        redis = get_redis()
        return bool(await redis.exists(self._key(key)))

    async def set_list(self, key: str, values: list[str], expire: Optional[int] = None) -> None:
        """设置列表"""
        redis = get_redis()
        full_key = self._key(key)
        await redis.delete(full_key)
        if values:
            await redis.rpush(full_key, *values)
        if expire:
            await redis.expire(full_key, expire)

    async def get_list(self, key: str, start: int = 0, end: int = -1) -> list[str]:
        """获取列表"""
        redis = get_redis()
        return await redis.lrange(self._key(key), start, end)

    async def push_to_list(self, key: str, value: str) -> None:
        """向列表末尾追加"""
        redis = get_redis()
        await redis.rpush(self._key(key), value)

    async def incr(self, key: str, amount: int = 1) -> int:
        """自增"""
        redis = get_redis()
        return await redis.incrby(self._key(key), amount)
