"""Unit tests for monotonic message timestamps in ChatService."""

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exceptions import AgentError
from src.models.message import MessageRole
from src.services.chat_service import ChatService


@pytest.mark.asyncio
@patch("src.services.chat_service.get_settings")
async def test_process_message_user_then_assistant_created_at_monotonic(mock_get_settings):
    conv_id = uuid4()
    user_msg_id = uuid4()
    assistant_msg_id = uuid4()

    mock_get_settings.return_value = SimpleNamespace(ENABLE_SEMANTIC_CACHE=True)

    service = ChatService(db=AsyncMock())
    service._get_or_create_conversation = AsyncMock(return_value=SimpleNamespace(id=conv_id, title=None))
    service.msg_repo = AsyncMock()
    service.msg_repo.create = AsyncMock(
        side_effect=[
            SimpleNamespace(id=user_msg_id),
            SimpleNamespace(id=assistant_msg_id),
        ]
    )
    service.memory_manager = AsyncMock()
    service.memory_manager.load_context = AsyncMock(return_value=[])
    service.memory_manager.save_turn = AsyncMock()
    service.semantic_cache = AsyncMock()
    service.semantic_cache.get = AsyncMock(return_value="cached response")
    service.conv_repo = AsyncMock()
    service.conv_repo.update_by_id = AsyncMock()

    await service.process_message(
        message="hello",
        conversation_id=None,
        user_id=None,
        context={},
        attachments=None,
        web_search=False,
    )

    user_created = service.msg_repo.create.await_args_list[0].args[0].created_at
    assistant_created = service.msg_repo.create.await_args_list[1].args[0].created_at
    user_role = service.msg_repo.create.await_args_list[0].args[0].role
    assistant_role = service.msg_repo.create.await_args_list[1].args[0].role

    assert user_role == MessageRole.USER
    assert assistant_role == MessageRole.ASSISTANT
    assert user_created < assistant_created


@pytest.mark.asyncio
async def test_process_message_error_created_at_not_earlier_than_user():
    conv_id = uuid4()

    service = ChatService(db=AsyncMock())
    service._get_or_create_conversation = AsyncMock(return_value=SimpleNamespace(id=conv_id, title=None))
    service.msg_repo = AsyncMock()
    service.msg_repo.create = AsyncMock(
        side_effect=[
            SimpleNamespace(id=uuid4()),
            SimpleNamespace(id=uuid4()),
        ]
    )
    service.memory_manager = AsyncMock()
    service.memory_manager.load_context = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(AgentError):
        await service.process_message(
            message="trigger error",
            conversation_id=None,
            user_id=None,
            context={},
            attachments=None,
            web_search=False,
        )

    user_created = service.msg_repo.create.await_args_list[0].args[0].created_at
    error_created = service.msg_repo.create.await_args_list[1].args[0].created_at
    user_role = service.msg_repo.create.await_args_list[0].args[0].role
    error_role = service.msg_repo.create.await_args_list[1].args[0].role

    assert user_role == MessageRole.USER
    assert error_role == MessageRole.ASSISTANT
    assert error_created >= user_created
