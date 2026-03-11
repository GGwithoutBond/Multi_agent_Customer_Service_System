"""
通知发送异步任务
"""

import asyncio
from typing import Optional

from src.core.logging import get_logger
from src.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="tasks.send_notification")
def send_notification(
    user_id: str,
    title: str,
    content: str,
    channel: str = "system",
) -> dict:
    """异步发送通知"""
    logger.info("发送通知: user=%s, title=%s", user_id, title)

    async def _run():
        from src.services.notification_service import NotificationService
        service = NotificationService()
        await service.send_notification(
            user_id=user_id,
            title=title,
            content=content,
            channel=channel,
        )

    asyncio.get_event_loop().run_until_complete(_run())
    return {"status": "sent", "user_id": user_id}


@celery_app.task(name="tasks.notify_human_transfer")
def notify_human_transfer(
    conversation_id: str,
    user_id: Optional[str] = None,
) -> dict:
    """异步通知人工客服转接"""
    logger.info("转人工通知: conversation=%s", conversation_id)

    async def _run():
        from src.services.notification_service import NotificationService
        service = NotificationService()
        await service.notify_human_transfer(
            conversation_id=conversation_id,
            user_id=user_id,
        )

    asyncio.get_event_loop().run_until_complete(_run())
    return {"status": "notified", "conversation_id": conversation_id}
