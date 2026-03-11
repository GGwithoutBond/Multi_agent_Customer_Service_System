"""
消息数据访问层
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.message import Message
from src.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """消息 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def get_by_conversation(
        self,
        conversation_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Message]:
        """获取会话的消息列表"""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def count_by_conversation(self, conversation_id: UUID) -> int:
        """统计会话消息数"""
        result = await self.session.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        return result.scalar_one()

    async def get_recent_messages(
        self, conversation_id: UUID, limit: int = 10
    ) -> Sequence[Message]:
        """获取会话最近 N 条消息"""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        # 返回时按时间正序
        messages = result.scalars().all()
        return list(reversed(messages))
