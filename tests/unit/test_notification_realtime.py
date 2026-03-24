from unittest.mock import AsyncMock, patch

import pytest

from src.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_notify_human_agent_broadcasts_to_admin_group():
    service = NotificationService()
    pool = AsyncMock()
    pool.broadcast_json = AsyncMock(return_value=1)

    with patch("src.services.notification_service.get_connection_pool", return_value=pool):
        await service.notify_human_agent(
            conversation_id="conv-1",
            user_message="need help",
            urgency="high",
            sentiment="negative",
            user_id="user-1",
        )

    pool.broadcast_json.assert_awaited_once()
    args = pool.broadcast_json.await_args.args
    assert args[0] == "admin_notifications"
    assert args[1]["type"] == "human_transfer"
    assert args[1]["conversation_id"] == "conv-1"
