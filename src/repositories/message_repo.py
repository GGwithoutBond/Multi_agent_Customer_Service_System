"""
Message repository.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.message import Message
from src.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Message repository."""

    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def get_by_conversation(
        self,
        conversation_id: UUID,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return result.scalars().all()

    async def count_by_conversation(self, conversation_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        return result.scalar_one()

    async def get_recent_messages(
        self, conversation_id: UUID, limit: int = 10
    ) -> Sequence[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))

    async def get_recent_by_conversation(
        self,
        conversation_id: UUID,
        limit: int = 30,
    ) -> Sequence[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))

    async def get_before_message(
        self,
        conversation_id: UUID,
        before_message_id: UUID,
        limit: int = 30,
    ) -> Sequence[Message]:
        cursor_message = await self.get_by_id(before_message_id)
        if not cursor_message or cursor_message.conversation_id != conversation_id:
            return []

        result = await self.session.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                or_(
                    Message.created_at < cursor_message.created_at,
                    and_(
                        Message.created_at == cursor_message.created_at,
                        Message.id < cursor_message.id,
                    ),
                ),
            )
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))

    async def exists_older_than(self, conversation_id: UUID, message_id: UUID) -> bool:
        cursor_message: Optional[Message] = await self.get_by_id(message_id)
        if not cursor_message or cursor_message.conversation_id != conversation_id:
            return False

        result = await self.session.execute(
            select(Message.id)
            .where(
                Message.conversation_id == conversation_id,
                or_(
                    Message.created_at < cursor_message.created_at,
                    and_(
                        Message.created_at == cursor_message.created_at,
                        Message.id < cursor_message.id,
                    ),
                ),
            )
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(1)
        )
        return result.first() is not None
