"""
Conversation service.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.core.logging import get_logger
from src.models.conversation import Conversation, ConversationChannel, ConversationStatus
from src.models.message import Message
from src.repositories.conversation_repo import ConversationRepository
from src.repositories.message_repo import MessageRepository

logger = get_logger(__name__)


class ConversationService:
    """Conversation domain service."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)

    async def create_conversation(
        self,
        user_id: Optional[UUID] = None,
        channel: str = "web",
        metadata: Optional[dict] = None,
    ) -> Conversation:
        conv = Conversation(
            user_id=user_id,
            channel=ConversationChannel(channel),
            status=ConversationStatus.ACTIVE,
            metadata_=metadata or {},
        )
        conv = await self.conv_repo.create(conv)
        logger.info("Created conversation %s (user=%s)", conv.id, user_id)
        return conv

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        conv = await self.conv_repo.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError("conversation", str(conversation_id))
        return conv

    async def get_conversation_for_user(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        conv = await self.conv_repo.get_by_id_for_user(conversation_id, user_id)
        if not conv:
            raise NotFoundError("conversation", str(conversation_id))
        return conv

    async def get_conversation_with_messages(self, conversation_id: UUID) -> Conversation:
        conv = await self.conv_repo.get_with_messages(conversation_id)
        if not conv:
            raise NotFoundError("conversation", str(conversation_id))
        return conv

    async def get_conversation_with_messages_for_user(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        conv = await self.conv_repo.get_with_messages_for_user(conversation_id, user_id)
        if not conv:
            raise NotFoundError("conversation", str(conversation_id))
        return conv

    async def list_conversations(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Conversation], int]:
        conv_status = ConversationStatus(status) if status else None
        offset = (page - 1) * page_size

        conversations = await self.conv_repo.get_by_user(
            user_id,
            status=conv_status,
            offset=offset,
            limit=page_size,
        )
        total = await self.conv_repo.count_by_user(user_id, status=conv_status)
        return conversations, total

    async def close_conversation(self, conversation_id: UUID) -> Conversation:
        conv = await self.conv_repo.close_conversation(conversation_id)
        if not conv:
            raise NotFoundError("conversation", str(conversation_id))
        logger.info("Closed conversation %s", conversation_id)
        return conv

    async def delete_conversation(self, conversation_id: UUID) -> bool:
        conv = await self.conv_repo.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError("conversation", str(conversation_id))
        deleted = await self.conv_repo.delete_by_id(conversation_id)
        if deleted:
            logger.info("Deleted conversation %s", conversation_id)
        return deleted

    async def delete_conversation_for_user(self, conversation_id: UUID, user_id: UUID) -> bool:
        conv = await self.conv_repo.get_by_id_for_user(conversation_id, user_id)
        if not conv:
            raise NotFoundError("conversation", str(conversation_id))
        deleted = await self.conv_repo.delete_by_id(conversation_id)
        if deleted:
            logger.info("Deleted conversation %s (user=%s)", conversation_id, user_id)
        return deleted

    async def update_conversation_for_user(
        self,
        conversation_id: UUID,
        user_id: UUID,
        **update_data,
    ) -> Conversation:
        conv = await self.conv_repo.update_by_id_for_user(conversation_id, user_id, **update_data)
        if not conv:
            raise NotFoundError("conversation", str(conversation_id))
        return conv

    async def update_pin_for_user(
        self,
        conversation_id: UUID,
        user_id: UUID,
        is_pinned: bool,
    ) -> Conversation:
        return await self.update_conversation_for_user(
            conversation_id,
            user_id,
            is_pinned=is_pinned,
        )

    async def batch_delete_for_user(
        self,
        user_id: UUID,
        conversation_ids: list[UUID],
    ) -> dict:
        deleted_ids, skipped_ids = await self.conv_repo.bulk_delete_by_ids_for_user(
            user_id=user_id,
            conversation_ids=conversation_ids,
        )
        return {
            "requested": len(conversation_ids),
            "deleted": len(deleted_ids),
            "skipped": len(skipped_ids),
            "skipped_ids": skipped_ids,
        }

    async def get_messages_history_for_user(
        self,
        conversation_id: UUID,
        user_id: UUID,
        before_id: Optional[UUID] = None,
        limit: int = 30,
    ) -> tuple[list[Message], bool, Optional[UUID]]:
        conv = await self.conv_repo.get_by_id_for_user(conversation_id, user_id)
        if not conv:
            raise NotFoundError("conversation", str(conversation_id))

        if before_id:
            messages = list(
                await self.msg_repo.get_before_message(
                    conversation_id=conversation_id,
                    before_message_id=before_id,
                    limit=limit,
                )
            )
        else:
            messages = list(
                await self.msg_repo.get_recent_by_conversation(
                    conversation_id=conversation_id,
                    limit=limit,
                )
            )

        if not messages:
            return [], False, None

        oldest_message_id = messages[0].id
        has_more = await self.msg_repo.exists_older_than(conversation_id, oldest_message_id)
        next_before_id = oldest_message_id if has_more else None
        return messages, has_more, next_before_id

    async def get_message_count(self, conversation_id: UUID) -> int:
        return await self.msg_repo.count_by_conversation(conversation_id)
