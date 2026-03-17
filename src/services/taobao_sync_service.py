"""
淘宝用户数据同步服务
将从 MCP Server 获取的淘宝用户信息持久化到 PostgreSQL
"""

from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.session import get_session_factory
from src.models.taobao_user_data import TaobaoUserData

logger = get_logger(__name__)

# ── MCP 工具名 → 数据库字段 映射 ──
# 根据淘宝 MCP Server 暴露的工具名称，映射到 TaobaoUserData 的字段
TOOL_FIELD_MAP: dict[str, str] = {
    # 工具名（小写）                     → 数据库字段
    "get_user_info":            "taobao_nick",       # 昵称 + 头像（特殊处理）
    "get_user_profile":         "taobao_nick",
    "get_addresses":            "addresses",
    "get_shipping_addresses":   "addresses",
    "get_contacts":             "contacts",
    "get_orders":               "orders",
    "get_order_list":           "orders",
    "get_order_history":        "orders",
    "get_cart":                 "cart_items",
    "get_cart_items":           "cart_items",
    "get_shopping_cart":        "cart_items",
    "get_browsing_history":     "browsing_history",
    "get_browse_history":       "browsing_history",
    "get_followed_shops":       "followed_shops",
    "get_favorite_shops":       "followed_shops",
    "get_wangwang_chats":       "wangwang_chats",
    "get_chat_history":         "wangwang_chats",
    "get_chat_records":         "wangwang_chats",
}


class TaobaoSyncService:
    """淘宝 MCP 数据同步服务"""

    @staticmethod
    async def sync_from_tool_results(
        tool_results: dict[str, Any],
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[TaobaoUserData]:
        """
        从 MCP 工具调用结果中提取用户数据并同步到数据库。

        Args:
            tool_results: {tool_name: tool_output} 字典，
                          由 mcp_client 在 agent 执行后收集。
            user_id: 本系统的用户 ID（可选）

        Returns:
            同步后的 TaobaoUserData 记录，或 None（无数据可同步时）
        """
        if not tool_results:
            return None

        # 过滤出与用户数据相关的工具调用结果
        sync_data: dict[str, Any] = {}
        taobao_nick = None
        taobao_avatar = None

        for tool_name, result in tool_results.items():
            tool_key = tool_name.lower().strip()

            # 处理用户基本信息（昵称 + 头像）
            if tool_key in ("get_user_info", "get_user_profile"):
                if isinstance(result, dict):
                    taobao_nick = result.get("nick") or result.get("nickname") or result.get("name")
                    taobao_avatar = result.get("avatar") or result.get("avatar_url") or result.get("head_img")
                elif isinstance(result, str):
                    taobao_nick = result
                continue

            # 映射到字段
            field = TOOL_FIELD_MAP.get(tool_key)
            if field:
                sync_data[field] = result

        # 没有任何可同步的数据
        if not sync_data and not taobao_nick:
            logger.debug("MCP 工具调用结果中没有可同步的用户数据")
            return None

        # ── 执行数据库 upsert ──
        try:
            factory = get_session_factory()
            async with factory() as session:
                record = await TaobaoSyncService._upsert(
                    session=session,
                    user_id=user_id,
                    taobao_nick=taobao_nick,
                    taobao_avatar=taobao_avatar,
                    sync_data=sync_data,
                    raw_data=tool_results,
                )
                await session.commit()

                logger.info(
                    "✅ 淘宝用户数据同步完成 | nick=%s user_id=%s fields=%s",
                    taobao_nick, user_id, list(sync_data.keys()),
                )
                return record

        except Exception as e:
            logger.error("淘宝用户数据同步失败: %s", e, exc_info=True)
            return None

    @staticmethod
    async def _upsert(
        session: AsyncSession,
        user_id: Optional[uuid.UUID],
        taobao_nick: Optional[str],
        taobao_avatar: Optional[str],
        sync_data: dict[str, Any],
        raw_data: dict[str, Any],
    ) -> TaobaoUserData:
        """按 user_id 或 taobao_nick 查找已有记录，存在则更新，否则新建"""

        record: Optional[TaobaoUserData] = None

        # 优先按 user_id 查找
        if user_id:
            stmt = select(TaobaoUserData).where(TaobaoUserData.user_id == user_id)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

        # 其次按淘宝昵称查找
        if not record and taobao_nick:
            stmt = select(TaobaoUserData).where(TaobaoUserData.taobao_nick == taobao_nick)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

        if record:
            # ── 更新已有记录 ──
            if taobao_nick:
                record.taobao_nick = taobao_nick
            if taobao_avatar:
                record.taobao_avatar = taobao_avatar
            for field, value in sync_data.items():
                setattr(record, field, value)
            record.raw_data = raw_data
            record.last_synced_at = datetime.now(timezone.utc)
        else:
            # ── 新建记录 ──
            record = TaobaoUserData(
                user_id=user_id,
                taobao_nick=taobao_nick,
                taobao_avatar=taobao_avatar,
                raw_data=raw_data,
                last_synced_at=datetime.now(timezone.utc),
                **sync_data,
            )
            session.add(record)

        # 回写用户表的 display_name / avatar_url（如果有关联用户）
        if user_id and (taobao_nick or taobao_avatar):
            await TaobaoSyncService._update_user_profile(session, user_id, taobao_nick, taobao_avatar)

        return record

    @staticmethod
    async def _update_user_profile(
        session: AsyncSession,
        user_id: uuid.UUID,
        nick: Optional[str],
        avatar: Optional[str],
    ) -> None:
        """将淘宝昵称和头像回写到 User 表"""
        from src.models.user import User

        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            if nick and not user.display_name:
                user.display_name = nick
            if avatar and not user.avatar_url:
                user.avatar_url = avatar
