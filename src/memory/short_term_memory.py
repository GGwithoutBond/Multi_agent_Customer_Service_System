"""
短期记忆 (Redis)
管理会话期间的对话历史，支持滑动窗口和摘要压缩
优化: 延长过期时间到 7 天
"""

import json
from typing import Any, Optional

from src.core.config import get_settings
from src.core.logging import get_logger
from src.database.redis import get_redis
from src.llm.token_counter import count_tokens
from src.memory.base import BaseMemory

logger = get_logger(__name__)


class ShortTermMemory(BaseMemory):
    """短期记忆 - 基于 Redis 的会话级记忆"""

    PREFIX = "memory:short"
    DEFAULT_EXPIRE = 3600 * 24 * 7  # 优化 3.3: 7 天过期（客服场景用户可能隔天追问）

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        max_turns: Optional[int] = None,
    ):
        settings = get_settings()
        self.max_tokens = max_tokens or settings.MEMORY_MAX_TOKENS
        self.max_turns = max_turns or settings.MEMORY_MAX_TURNS

    def _key(self, session_id: str) -> str:
        return f"{self.PREFIX}:{session_id}"

    async def load(self, session_id: str) -> list[dict[str, Any]]:
        """加载会话的对话历史"""
        redis = get_redis()
        data = await redis.get(self._key(session_id))
        if data:
            return json.loads(data)
        return []

    async def save(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """保存对话历史 (自动应用滑动窗口)"""
        trimmed = self._trim_by_turns(messages)
        trimmed = self._trim_by_tokens(trimmed)

        redis = get_redis()
        await redis.set(
            self._key(session_id),
            json.dumps(trimmed, ensure_ascii=False, default=str),
            ex=self.DEFAULT_EXPIRE,
        )

    async def add_message(self, session_id: str, message: dict[str, Any]) -> None:
        """追加一条消息"""
        messages = await self.load(session_id)
        messages.append(message)
        await self.save(session_id, messages)

    async def clear(self, session_id: str) -> None:
        """清除会话记忆"""
        redis = get_redis()
        await redis.delete(self._key(session_id))

    def _trim_by_turns(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按轮次裁剪"""
        if len(messages) <= self.max_turns * 2:
            return messages
        # 保留最后 max_turns 轮对话 (每轮 2 条消息)
        return messages[-(self.max_turns * 2):]

    def _trim_by_tokens(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按 Token 数裁剪"""
        total_tokens = sum(
            count_tokens(msg.get("content", "")) for msg in messages
        )
        while total_tokens > self.max_tokens and len(messages) > 2:
            removed = messages.pop(0)
            total_tokens -= count_tokens(removed.get("content", ""))
        return messages

    async def get_summary(self, session_id: str) -> Optional[str]:
        """获取会话摘要"""
        redis = get_redis()
        return await redis.get(f"{self.PREFIX}:summary:{session_id}")

    async def set_summary(self, session_id: str, summary: str) -> None:
        """保存会话摘要"""
        redis = get_redis()
        await redis.set(
            f"{self.PREFIX}:summary:{session_id}",
            summary,
            ex=self.DEFAULT_EXPIRE,
        )
