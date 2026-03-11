"""
Human Worker Agent
处理转人工服务 —— 支持 WebSocket 通知和排队信息
"""

from typing import Any

from src.agents.workers.base_worker import BaseWorker
from src.core.logging import get_logger

logger = get_logger(__name__)


class HumanWorker(BaseWorker):
    """转人工 Worker"""

    def __init__(self):
        super().__init__(
            name="human_worker",
            description="处理转人工客服请求",
        )

    async def handle(self, user_input: str, context: dict[str, Any], history: str = "") -> str:
        """转人工处理逻辑"""
        sentiment = context.get("sentiment", "neutral")
        urgency = context.get("urgency", "medium")

        logger.info(
            "🙋 用户请求转人工服务 | sentiment=%s urgency=%s | %s",
            sentiment, urgency, user_input[:100],
        )

        # 通知人工客服（通过 NotificationService）
        try:
            from src.services.notification_service import NotificationService
            notification = NotificationService()
            await notification.notify_human_agent(
                conversation_id=context.get("conversation_id", "unknown"),
                user_message=user_input,
                urgency=urgency,
                sentiment=sentiment,
            )
        except Exception as e:
            logger.warning("通知人工客服失败: %s", e)

        # 根据紧急度调整回复
        if urgency in ("high", "critical") or sentiment == "angry":
            return (
                "我理解您的心情，非常抱歉给您带来不好的体验 😔\n\n"
                "已为您标记为**加急处理**，人工客服将优先接待您。\n"
                "预计等待时间：1-2 分钟。\n\n"
                "在等待期间，您可以继续描述问题详情，人工客服接入后会第一时间查看。"
            )
        else:
            return (
                "好的，正在为您转接人工客服 🙋\n\n"
                "当前排队人数较少，预计等待时间：3-5 分钟。\n\n"
                "在等待期间，您可以继续描述您的问题，以便人工客服更快了解您的需求。"
            )
