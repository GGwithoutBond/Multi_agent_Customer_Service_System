"""
会话模型
"""

import enum
import uuid
from typing import Optional

from sqlalchemy import String, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin, TimestampMixin


class ConversationStatus(str, enum.Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    CLOSED = "closed"
    TRANSFERRED = "transferred"


class ConversationChannel(str, enum.Enum):
    """接入渠道枚举"""
    WEB = "web"
    APP = "app"
    WECHAT = "wechat"
    API = "api"


class Conversation(Base, UUIDMixin, TimestampMixin):
    """会话表"""

    __tablename__ = "conversations"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel: Mapped[ConversationChannel] = mapped_column(
        Enum(ConversationChannel), default=ConversationChannel.WEB, nullable=False
    )
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.ACTIVE, nullable=False, index=True
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True, default=dict)

    # 关联
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", lazy="selectin",
        order_by="Message.created_at", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id} [{self.status.value}]>"
