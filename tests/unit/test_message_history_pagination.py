from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import NotFoundError
from src.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_message_history_requires_owned_conversation():
    conversation_id = uuid4()
    user_id = uuid4()

    service = ConversationService(db=AsyncMock())
    service.conv_repo = AsyncMock()
    service.msg_repo = AsyncMock()
    service.conv_repo.get_by_id_for_user = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.get_messages_history_for_user(conversation_id=conversation_id, user_id=user_id)


@pytest.mark.asyncio
async def test_message_history_initial_load_recent_items_and_cursor():
    conversation_id = uuid4()
    user_id = uuid4()
    oldest_id = uuid4()
    newest_id = uuid4()
    conv = SimpleNamespace(id=conversation_id, user_id=user_id)
    messages = [
        SimpleNamespace(id=oldest_id, conversation_id=conversation_id),
        SimpleNamespace(id=newest_id, conversation_id=conversation_id),
    ]

    service = ConversationService(db=AsyncMock())
    service.conv_repo = AsyncMock()
    service.msg_repo = AsyncMock()
    service.conv_repo.get_by_id_for_user = AsyncMock(return_value=conv)
    service.msg_repo.get_recent_by_conversation = AsyncMock(return_value=messages)
    service.msg_repo.exists_older_than = AsyncMock(return_value=True)

    items, has_more, next_before_id = await service.get_messages_history_for_user(
        conversation_id=conversation_id,
        user_id=user_id,
        limit=30,
    )

    assert items == messages
    assert has_more is True
    assert next_before_id == oldest_id
    service.msg_repo.get_recent_by_conversation.assert_awaited_once_with(
        conversation_id=conversation_id,
        limit=30,
    )


@pytest.mark.asyncio
async def test_message_history_before_cursor_loads_older_items():
    conversation_id = uuid4()
    user_id = uuid4()
    before_id = uuid4()
    conv = SimpleNamespace(id=conversation_id, user_id=user_id)
    older = [SimpleNamespace(id=uuid4(), conversation_id=conversation_id)]

    service = ConversationService(db=AsyncMock())
    service.conv_repo = AsyncMock()
    service.msg_repo = AsyncMock()
    service.conv_repo.get_by_id_for_user = AsyncMock(return_value=conv)
    service.msg_repo.get_before_message = AsyncMock(return_value=older)
    service.msg_repo.exists_older_than = AsyncMock(return_value=False)

    items, has_more, next_before_id = await service.get_messages_history_for_user(
        conversation_id=conversation_id,
        user_id=user_id,
        before_id=before_id,
        limit=20,
    )

    assert items == older
    assert has_more is False
    assert next_before_id is None
    service.msg_repo.get_before_message.assert_awaited_once_with(
        conversation_id=conversation_id,
        before_message_id=before_id,
        limit=20,
    )
