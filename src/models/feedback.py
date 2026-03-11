"""
反馈模型
用户对消息的评价反馈
"""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin, TimestampMixin


class Feedback(Base, UUIDMixin, TimestampMixin):
    """用户反馈表"""

    __tablename__ = "feedbacks"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False, comment="评分: 1-5")
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 关联
    message = relationship("Message", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<Feedback message={self.message_id} rating={self.rating}>"
