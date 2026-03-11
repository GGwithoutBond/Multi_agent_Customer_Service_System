"""
用户画像模型
存储用户偏好、交互历史等长期记忆
"""

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Float

from src.models.base import Base, UUIDMixin, TimestampMixin


class UserProfile(Base, UUIDMixin, TimestampMixin):
    """用户画像表"""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True
    )
    preferences: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    interaction_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entities: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)

    # 关联
    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile user={self.user_id}>"
