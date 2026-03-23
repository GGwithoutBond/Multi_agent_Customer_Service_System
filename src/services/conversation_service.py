"""
会话管理服务
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.core.logging import get_logger
from src.models.conversation import Conversation, ConversationChannel, ConversationStatus
from src.repositories.conversation_repo import ConversationRepository
from src.repositories.message_repo import MessageRepository

logger = get_logger(__name__)


class ConversationService:
    """会话管理服务"""

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
        """创建新会话"""
        conv = Conversation(
            user_id=user_id,
            channel=ConversationChannel(channel),
            status=ConversationStatus.ACTIVE,
            metadata_=metadata or {},
        )
        conv = await self.conv_repo.create(conv)
        logger.info("创建新会话: %s (用户: %s)", conv.id, user_id)
        return conv

    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        """获取会话详情"""
        conv = await self.conv_repo.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError("会话", str(conversation_id))
        return conv

    async def get_conversation_for_user(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        """获取当前用户拥有的会话详情。"""
        conv = await self.conv_repo.get_by_id_for_user(conversation_id, user_id)
        if not conv:
            raise NotFoundError("会话", str(conversation_id))
        return conv

    async def get_conversation_with_messages(self, conversation_id: UUID) -> Conversation:
        """获取会话及其消息"""
        conv = await self.conv_repo.get_with_messages(conversation_id)
        if not conv:
            raise NotFoundError("会话", str(conversation_id))
        return conv

    async def get_conversation_with_messages_for_user(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        """获取当前用户拥有的会话及其消息。"""
        conv = await self.conv_repo.get_with_messages_for_user(conversation_id, user_id)
        if not conv:
            raise NotFoundError("会话", str(conversation_id))
        return conv

    async def list_conversations(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Conversation], int]:
        """获取用户的会话列表"""
        conv_status = ConversationStatus(status) if status else None
        offset = (page - 1) * page_size

        conversations = await self.conv_repo.get_by_user(
            user_id, status=conv_status, offset=offset, limit=page_size
        )
        total = await self.conv_repo.count_by_user(user_id, status=conv_status)

        return conversations, total

    async def close_conversation(self, conversation_id: UUID) -> Conversation:
        """关闭会话"""
        conv = await self.conv_repo.close_conversation(conversation_id)
        if not conv:
            raise NotFoundError("会话", str(conversation_id))
        logger.info("会话已关闭: %s", conversation_id)
        return conv

    async def delete_conversation(self, conversation_id: UUID) -> bool:
        """删除会话（物理删除，级联删除消息）"""
        conv = await self.conv_repo.get_by_id(conversation_id)
        if not conv:
            raise NotFoundError("会话", str(conversation_id))
        deleted = await self.conv_repo.delete_by_id(conversation_id)
        if deleted:
            logger.info("会话已删除: %s", conversation_id)
        return deleted

    async def delete_conversation_for_user(self, conversation_id: UUID, user_id: UUID) -> bool:
        """删除当前用户拥有的会话。"""
        conv = await self.conv_repo.get_by_id_for_user(conversation_id, user_id)
        if not conv:
            raise NotFoundError("会话", str(conversation_id))
        deleted = await self.conv_repo.delete_by_id(conversation_id)
        if deleted:
            logger.info("会话已删除: %s user=%s", conversation_id, user_id)
        return deleted

    async def update_conversation_for_user(
        self,
        conversation_id: UUID,
        user_id: UUID,
        **update_data,
    ) -> Conversation:
        """更新当前用户拥有的会话。"""
        conv = await self.conv_repo.update_by_id_for_user(conversation_id, user_id, **update_data)
        if not conv:
            raise NotFoundError("会话", str(conversation_id))
        return conv

    async def get_message_count(self, conversation_id: UUID) -> int:
        """获取会话的消息数"""
        return await self.msg_repo.count_by_conversation(conversation_id)
