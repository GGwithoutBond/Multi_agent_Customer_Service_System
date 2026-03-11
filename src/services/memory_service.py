"""
记忆管理服务
提供记忆相关的业务操作接口
"""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.memory.memory_manager import MemoryManager

logger = get_logger(__name__)


class MemoryService:
    """记忆管理服务"""

    def __init__(self, db: AsyncSession):
        self.memory_manager = MemoryManager(db_session=db)

    async def get_conversation_context(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """获取会话上下文"""
        messages = await self.memory_manager.load_context(
            conversation_id=conversation_id,
            user_id=user_id,
        )
        return [
            {"role": msg.type, "content": msg.content}
            for msg in messages
        ]

    async def clear_conversation_memory(self, conversation_id: str) -> None:
        """清除会话的短期记忆"""
        await self.memory_manager.clear_session(conversation_id)
        logger.info("已清除会话 %s 的记忆", conversation_id)

    async def update_user_profile(
        self,
        user_id: str,
        entities: Optional[dict] = None,
        preferences: Optional[dict] = None,
        tags: Optional[list[str]] = None,
    ) -> None:
        """更新用户画像"""
        await self.memory_manager.update_user_profile(
            user_id=user_id,
            entities=entities,
            preferences=preferences,
            tags=tags,
        )
        logger.info("已更新用户 %s 的画像", user_id)
