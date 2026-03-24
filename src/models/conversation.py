"""
会话模型
"""

import enum
import uuid
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin, TimestampMixin


class ConversationStatus(str, enum.Enum):
    """会话状态枚举

    完整状态机:
    - INIT: 初始化，用户刚进入但还未发送消息
    - ACTIVE: 活跃中，AI 正在处理
    - WAITING: 等待中，等待用户回复（如多轮澄清）
    - TRANSFERRING: 转接中，正在转接到人工
    - TRANSFERRED: 已转接，已转接到人工坐席
    - CLOSED: 已关闭，会话正常结束
    - TIMEOUT: 超时，用户长时间无活动
    """
    INIT = "init"
    ACTIVE = "active"
    WAITING = "waiting"
    TRANSFERRING = "transferring"
    TRANSFERRED = "transferred"
    CLOSED = "closed"
    TIMEOUT = "timeout"


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
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True, default=dict)

    # 关联
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", lazy="selectin",
        order_by="Message.created_at", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id} [{self.status.value}]>"
