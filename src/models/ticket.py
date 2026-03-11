"""
工单（Ticket）ORM 模型
用于记录用户投诉、反馈工单
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDMixin


class TicketStatus(str, Enum):
    """工单状态"""
    OPEN = "open"           # 新建/待处理
    IN_PROGRESS = "in_progress"  # 处理中
    RESOLVED = "resolved"   # 已解决
    CLOSED = "closed"       # 已关闭
    ESCALATED = "escalated" # 已升级为人工


class TicketPriority(str, Enum):
    """工单优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ticket(Base, UUIDMixin, TimestampMixin):
    """投诉工单模型"""

    __tablename__ = "tickets"

    # 关联的会话
    conversation_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)

    # 用户 ID（可选，匿名用户也可以提交）
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # 工单标题（自动生成或 LLM 提取）
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="用户投诉")

    # 投诉详情内容
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # 投诉类型（quality/service/logistics/refund/other）
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False, default="other")

    # 情感状态（来自 Orchestrator 分析）
    sentiment: Mapped[str] = mapped_column(String(32), nullable=False, default="neutral")

    # 工单状态
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status"),
        default=TicketStatus.OPEN,
        nullable=False,
    )

    # 优先级
    priority: Mapped[TicketPriority] = mapped_column(
        SAEnum(TicketPriority, name="ticket_priority"),
        default=TicketPriority.MEDIUM,
        nullable=False,
    )

    # 处理备注
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} status={self.status} priority={self.priority}>"
