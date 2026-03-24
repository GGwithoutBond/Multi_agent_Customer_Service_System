"""
Conversation repository.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.conversation import Conversation, ConversationStatus
from src.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Conversation repository."""

    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def get_with_messages(self, conversation_id: UUID) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(self, conversation_id: UUID, user_id: UUID) -> Optional[Conversation]:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_with_messages_for_user(self, conversation_id: UUID, user_id: UUID) -> Optional[Conversation]:
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
        stmt = select(Conversation).where(Conversation.user_id == user_id)
        if status:
            stmt = stmt.where(Conversation.status == status)
        stmt = stmt.order_by(
            desc(Conversation.is_pinned),
            Conversation.updated_at.desc(),
        ).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_user(
        self, user_id: UUID, status: Optional[ConversationStatus] = None
    ) -> int:
        stmt = select(func.count()).select_from(Conversation).where(
            Conversation.user_id == user_id
        )
        if status:
            stmt = stmt.where(Conversation.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def close_conversation(self, conversation_id: UUID) -> Optional[Conversation]:
        return await self.update_by_id(conversation_id, status=ConversationStatus.CLOSED)

    async def update_by_id_for_user(
        self,
        conversation_id: UUID,
        user_id: UUID,
        **kwargs,
    ) -> Optional[Conversation]:
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

    async def bulk_delete_by_ids_for_user(
        self,
        user_id: UUID,
        conversation_ids: Sequence[UUID],
    ) -> tuple[list[UUID], list[UUID]]:
        if not conversation_ids:
            return [], []

        requested = list(dict.fromkeys(conversation_ids))
        result = await self.session.execute(
            select(Conversation.id).where(
                Conversation.user_id == user_id,
                Conversation.id.in_(requested),
            )
        )
        owned_ids = [row[0] for row in result.all()]
        owned_set = set(owned_ids)
        skipped_ids = [cid for cid in requested if cid not in owned_set]

        if owned_ids:
            await self.session.execute(
                delete(Conversation).where(
                    Conversation.user_id == user_id,
                    Conversation.id.in_(owned_ids),
                )
            )
            await self.session.flush()

        return owned_ids, skipped_ids
