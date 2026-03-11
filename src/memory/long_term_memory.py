"""
长期记忆 (PostgreSQL + Vector)
跨会话持久化的用户画像和交互历史
"""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.memory.base import BaseMemory
from src.models.user_profile import UserProfile

logger = get_logger(__name__)


class LongTermMemory(BaseMemory):
    """长期记忆 - 基于 PostgreSQL 的持久化记忆"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def load(self, session_id: str) -> list[dict[str, Any]]:
        """加载用户画像（session_id 此处为 user_id）"""
        try:
            user_id = UUID(session_id)
        except ValueError:
            return []

        result = await self.session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            return [{
                "preferences": profile.preferences or {},
                "interaction_summary": profile.interaction_summary or "",
                "entities": profile.entities or {},
                "tags": profile.tags or [],
            }]
        return []

    async def save(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """更新用户画像"""
        try:
            user_id = UUID(session_id)
        except ValueError:
            return

        if not messages:
            return

        data = messages[0]  # 取第一条作为画像数据
        result = await self.session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            if "preferences" in data:
                profile.preferences = {**(profile.preferences or {}), **data["preferences"]}
            if "interaction_summary" in data:
                profile.interaction_summary = data["interaction_summary"]
            if "entities" in data:
                profile.entities = {**(profile.entities or {}), **data["entities"]}
            if "tags" in data:
                existing_tags = profile.tags or []
                new_tags = list(set(existing_tags + data.get("tags", [])))
                profile.tags = new_tags
        else:
            profile = UserProfile(
                user_id=user_id,
                preferences=data.get("preferences", {}),
                interaction_summary=data.get("interaction_summary", ""),
                entities=data.get("entities", {}),
                tags=data.get("tags", []),
            )
            self.session.add(profile)

        await self.session.flush()

    async def clear(self, session_id: str) -> None:
        """清除用户长期记忆"""
        try:
            user_id = UUID(session_id)
        except ValueError:
            return

        result = await self.session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            profile.preferences = {}
            profile.interaction_summary = None
            profile.entities = {}
            profile.tags = []
            await self.session.flush()
