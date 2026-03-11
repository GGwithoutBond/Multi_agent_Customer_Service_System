"""
记忆更新异步任务
"""

import asyncio
from typing import Any, Optional

from src.core.logging import get_logger
from src.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="tasks.update_user_profile")
def update_user_profile(
    user_id: str,
    entities: Optional[dict] = None,
    preferences: Optional[dict] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """异步更新用户画像"""
    logger.info("开始更新用户画像: %s", user_id)

    async def _run():
        from src.database.session import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            from src.services.memory_service import MemoryService
            service = MemoryService(session)
            await service.update_user_profile(
                user_id=user_id,
                entities=entities,
                preferences=preferences,
                tags=tags,
            )
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_run())
    logger.info("用户画像更新完成: %s", user_id)
    return {"status": "completed", "user_id": user_id}
