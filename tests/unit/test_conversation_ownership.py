from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from src.core.exceptions import NotFoundError
from src.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_get_conversation_for_user_returns_owned_conversation():
    conversation_id = uuid4()
    user_id = uuid4()
    conv = SimpleNamespace(id=conversation_id, user_id=user_id)

    service = ConversationService(db=AsyncMock())
    service.conv_repo = AsyncMock()
    service.conv_repo.get_by_id_for_user = AsyncMock(return_value=conv)

    result = await service.get_conversation_for_user(conversation_id, user_id)
    assert result == conv


@pytest.mark.asyncio
async def test_get_conversation_for_user_non_owner_raises_not_found():
    conversation_id = uuid4()
    user_id = uuid4()

    service = ConversationService(db=AsyncMock())
    service.conv_repo = AsyncMock()
    service.conv_repo.get_by_id_for_user = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.get_conversation_for_user(conversation_id, user_id)


@pytest.mark.asyncio
async def test_update_conversation_for_user_non_owner_raises_not_found():
    conversation_id = uuid4()
    user_id = uuid4()

    service = ConversationService(db=AsyncMock())
    service.conv_repo = AsyncMock()
    service.conv_repo.update_by_id_for_user = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.update_conversation_for_user(conversation_id, user_id, title="new title")


@pytest.mark.asyncio
async def test_delete_conversation_for_user_non_owner_raises_not_found():
    conversation_id = uuid4()
    user_id = uuid4()

    service = ConversationService(db=AsyncMock())
    service.conv_repo = AsyncMock()
    service.conv_repo.get_by_id_for_user = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.delete_conversation_for_user(conversation_id, user_id)

