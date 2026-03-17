"""
淘宝用户数据模型
存储从淘宝 MCP Server 同步的用户个人信息
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin, TimestampMixin


class TaobaoUserData(Base, UUIDMixin, TimestampMixin):
    """淘宝用户数据表 — 存储从 MCP 同步的全量用户信息"""

    __tablename__ = "taobao_user_data"

    # 关联本系统用户（可选，未登录时为空）
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )

    # ── 淘宝基本信息 ──
    taobao_nick: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True, comment="淘宝昵称")
    taobao_avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="淘宝头像 URL")

    # ── 收货地址 & 联系人 ──
    addresses: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list, comment="收货地址列表")
    contacts: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list, comment="联系人信息")

    # ── 订单 & 购物车 ──
    orders: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list, comment="历史订单记录")
    cart_items: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list, comment="购物车内容")

    # ── 浏览 & 关注 ──
    browsing_history: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list, comment="浏览记录")
    followed_shops: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list, comment="关注店铺")

    # ── 旺旺聊天记录 ──
    wangwang_chats: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list, comment="旺旺聊天记录")

    # ── 原始数据兜底 ──
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=dict, comment="MCP 返回的完整原始 JSON")

    # ── 最近同步时间 ──
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近一次 MCP 同步时间",
    )

    # 关联
    user = relationship("User", backref="taobao_data", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TaobaoUserData nick={self.taobao_nick} user_id={self.user_id}>"
