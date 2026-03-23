"""
会话数据访问层
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.conversation import Conversation, ConversationStatus
from src.models.message import Message
from src.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """会话 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def get_with_messages(self, conversation_id: UUID) -> Optional[Conversation]:
        """获取会话及其所有消息"""
        result = await self.session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(self, conversation_id: UUID, user_id: UUID) -> Optional[Conversation]:
        """按会话 ID + 用户 ID 查询会话。"""
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_with_messages_for_user(self, conversation_id: UUID, user_id: UUID) -> Optional[Conversation]:
        """按会话 ID + 用户 ID 查询会话及其消息。"""
        result = await self.session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: UUID,
        status: Optional[ConversationStatus] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Sequence[Conversation]:
        """根据用户 ID 查询会话列表"""
        stmt = select(Conversation).where(Conversation.user_id == user_id)
        if status:
            stmt = stmt.where(Conversation.status == status)
        stmt = stmt.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_user(
        self, user_id: UUID, status: Optional[ConversationStatus] = None
    ) -> int:
        """统计用户会话数"""
        stmt = select(func.count()).select_from(Conversation).where(
            Conversation.user_id == user_id
        )
        if status:
            stmt = stmt.where(Conversation.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def close_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        """关闭会话"""
        return await self.update_by_id(conversation_id, status=ConversationStatus.CLOSED)

    async def update_by_id_for_user(self, conversation_id: UUID, user_id: UUID, **kwargs) -> Optional[Conversation]:
        """按会话归属更新会话。"""
        await self.session.execute(
            update(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .values(**kwargs)
        )
        await self.session.flush()
        return await self.get_by_id_for_user(conversation_id, user_id)
