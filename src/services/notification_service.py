"""
Notification service.
"""

from typing import Any, Optional

from src.core.logging import get_logger
from src.services.connection_pool import get_connection_pool

logger = get_logger(__name__)


class NotificationService:
    """Handles system notifications and human-transfer events."""

    async def notify_human_agent(
        self,
        conversation_id: str,
        user_message: str = "",
        urgency: str = "medium",
        sentiment: str = "neutral",
        user_id: Optional[str] = None,
    ) -> None:
        notification_data = {
            "type": "human_transfer",
            "conversation_id": conversation_id,
            "user_id": user_id,
            "user_message": user_message[:200],
            "urgency": urgency,
            "sentiment": sentiment,
            "priority": self._calculate_priority(urgency, sentiment),
        }

        pool = get_connection_pool()
        delivered = await pool.broadcast_json("admin_notifications", notification_data)

        logger.info(
            "Human transfer notification conversation=%s urgency=%s sentiment=%s priority=%s delivered=%s",
            conversation_id,
            urgency,
            sentiment,
            notification_data["priority"],
            delivered,
        )

    async def notify_human_transfer(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        await self.notify_human_agent(
            conversation_id=conversation_id,
            user_id=user_id,
        )

    async def send_notification(
        self,
        user_id: str,
        title: str,
        content: str,
        channel: str = "system",
    ) -> None:
        notification_data = {
            "type": "notification",
            "user_id": user_id,
            "title": title,
            "content": content,
            "channel": channel,
        }

        delivered = await get_connection_pool().broadcast_json(f"user:{user_id}", notification_data)
        logger.info(
            "Notification sent user=%s channel=%s title=%s delivered=%s",
            user_id,
            channel,
            title,
            delivered,
        )

    async def send_satisfaction_survey(
        self,
        conversation_id: str,
        user_id: str,
    ) -> None:
        await self.send_notification(
            user_id=user_id,
            title="服务评价",
            content="感谢您的耐心等待，请对本次服务进行评价。",
            channel="survey",
        )
        logger.info("Satisfaction survey queued conversation=%s", conversation_id)

    @staticmethod
    def _calculate_priority(urgency: str, sentiment: str) -> int:
        urgency_scores = {"low": 1, "medium": 2, "high": 3, "critical": 5}
        sentiment_boost = {"angry": 2, "negative": 1, "neutral": 0, "positive": 0}
        base = urgency_scores.get(urgency, 2)
        boost = sentiment_boost.get(sentiment, 0)
        return min(base + boost, 5)


async def register_connection(
    connection_id: str,
    websocket: Any,
    groups: Optional[list[str]] = None,
) -> None:
    await get_connection_pool().register(connection_id, websocket, groups=groups or [])


async def unregister_connection(connection_id: str) -> None:
    await get_connection_pool().unregister(connection_id)
