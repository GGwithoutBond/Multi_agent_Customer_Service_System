"""
通知服务
处理系统通知、转人工通知、WebSocket 推送
"""

import json
from typing import Any, Optional

from src.core.logging import get_logger

logger = get_logger(__name__)

# 全局 WebSocket 连接池（简化实现）
_active_connections: dict[str, Any] = {}


class NotificationService:
    """通知服务"""

    async def notify_human_agent(
        self,
        conversation_id: str,
        user_message: str = "",
        urgency: str = "medium",
        sentiment: str = "neutral",
        user_id: Optional[str] = None,
    ) -> None:
        """
        通知人工客服接入请求
        通过 WebSocket 推送到管理后台 + 日志记录
        """
        notification_data = {
            "type": "human_transfer",
            "conversation_id": conversation_id,
            "user_id": user_id,
            "user_message": user_message[:200],
            "urgency": urgency,
            "sentiment": sentiment,
            "priority": self._calculate_priority(urgency, sentiment),
        }

        # 尝试通过 WebSocket 推送
        await self._broadcast_to_admins(notification_data)

        # 日志记录（生产环境应对接消息队列）
        logger.info(
            "🔔 转人工通知 | conversation=%s urgency=%s sentiment=%s priority=%s",
            conversation_id,
            urgency,
            sentiment,
            notification_data["priority"],
        )

    async def notify_human_transfer(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """兼容旧接口的转人工通知"""
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
        """发送通知"""
        notification_data = {
            "type": "notification",
            "user_id": user_id,
            "title": title,
            "content": content,
            "channel": channel,
        }

        # 尝试 WebSocket 推送给用户
        if user_id in _active_connections:
            try:
                ws = _active_connections[user_id]
                await ws.send_text(json.dumps(notification_data, ensure_ascii=False))
            except Exception as e:
                logger.warning("WebSocket 推送失败: %s", e)

        logger.info(
            "📢 发送通知: user=%s, channel=%s, title=%s",
            user_id,
            channel,
            title,
        )

    async def send_satisfaction_survey(
        self,
        conversation_id: str,
        user_id: str,
    ) -> None:
        """发送满意度调查通知"""
        await self.send_notification(
            user_id=user_id,
            title="服务评价",
            content="感谢您的耐心等待！请对本次服务进行评价 ⭐",
            channel="survey",
        )
        logger.info("📊 满意度调查已发送: conversation=%s", conversation_id)

    @staticmethod
    def _calculate_priority(urgency: str, sentiment: str) -> int:
        """计算优先级分数（1-5, 5 为最高）"""
        urgency_scores = {"low": 1, "medium": 2, "high": 3, "critical": 5}
        sentiment_boost = {"angry": 2, "negative": 1, "neutral": 0, "positive": 0}
        base = urgency_scores.get(urgency, 2)
        boost = sentiment_boost.get(sentiment, 0)
        return min(base + boost, 5)

    async def _broadcast_to_admins(self, data: dict) -> None:
        """广播到所有管理员 WebSocket 连接"""
        # 遍历以 admin_ 开头的连接
        disconnected = []
        for conn_id, ws in _active_connections.items():
            if conn_id.startswith("admin_"):
                try:
                    await ws.send_text(json.dumps(data, ensure_ascii=False))
                except Exception:
                    disconnected.append(conn_id)
        for conn_id in disconnected:
            _active_connections.pop(conn_id, None)


def register_connection(connection_id: str, websocket: Any) -> None:
    """注册 WebSocket 连接"""
    _active_connections[connection_id] = websocket
    logger.info("WebSocket 连接注册: %s (总连接数: %d)", connection_id, len(_active_connections))


def unregister_connection(connection_id: str) -> None:
    """注销 WebSocket 连接"""
    _active_connections.pop(connection_id, None)
    logger.info("WebSocket 连接注销: %s", connection_id)
