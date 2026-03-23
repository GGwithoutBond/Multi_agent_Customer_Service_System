"""Unit tests for streaming chat behavior."""

import os
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ["DEBUG"] = "false"

from src.services.chat_service import ChatService


class FakeWorkflow:
    def __init__(self, events):
        self._events = events

    async def astream(self, _state):
        for event in self._events:
            yield event


@pytest.mark.asyncio
@patch("src.services.chat_service.get_settings")
async def test_stream_emits_meta_with_conversation_id(mock_get_settings):
    conv_id = uuid4()
    done_message_id = uuid4()

    mock_get_settings.return_value = SimpleNamespace(
        ENABLE_SEMANTIC_CACHE=True,
        ENABLE_ASYNC_POSTPROCESS=False,
        ENABLE_SYNC_FIRST_TURN_SUMMARY=False,
        ENABLE_SYNC_QUALITY_REVIEW=True,
        SYNC_QUALITY_REVIEW_RISK_ONLY=True,
        ENABLE_ASYNC_QUALITY_REVIEW=False,
    )

    service = ChatService(db=AsyncMock())
    service._get_or_create_conversation = AsyncMock(return_value=SimpleNamespace(id=conv_id))
    service.msg_repo = AsyncMock()
    service.msg_repo.create = AsyncMock(side_effect=[SimpleNamespace(id=uuid4()), SimpleNamespace(id=done_message_id)])
    service.memory_manager = AsyncMock()
    service.memory_manager.load_context = AsyncMock(return_value=[])
    service.semantic_cache = AsyncMock()
    service.semantic_cache.get = AsyncMock(return_value="cached stream response")
    service._run_stream_postprocess = AsyncMock()

    chunks = [
        chunk
        async for chunk in service.process_message_stream(
            message="hello",
            conversation_id=None,
            user_id=None,
            context={},
            attachments=None,
            web_search=False,
        )
    ]

    assert chunks[0].type == "meta"
    assert chunks[0].conversation_id == conv_id
    assert any(chunk.type == "chunk" for chunk in chunks)
    assert chunks[-1].type == "done"
    assert chunks[-1].message_id == done_message_id


@pytest.mark.asyncio
@patch("src.services.chat_service.asyncio.create_task")
@patch("src.services.chat_service.get_settings")
async def test_stream_done_before_async_postprocess(mock_get_settings, mock_create_task):
    conv_id = uuid4()

    mock_get_settings.return_value = SimpleNamespace(
        ENABLE_SEMANTIC_CACHE=True,
        ENABLE_ASYNC_POSTPROCESS=True,
        ENABLE_SYNC_FIRST_TURN_SUMMARY=False,
        ENABLE_SYNC_QUALITY_REVIEW=True,
        SYNC_QUALITY_REVIEW_RISK_ONLY=True,
        ENABLE_ASYNC_QUALITY_REVIEW=False,
    )
    mock_create_task.side_effect = lambda coro: (coro.close(), MagicMock())[1]

    service = ChatService(db=AsyncMock())
    service._get_or_create_conversation = AsyncMock(return_value=SimpleNamespace(id=conv_id))
    service.msg_repo = AsyncMock()
    service.msg_repo.create = AsyncMock(side_effect=[SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())])
    service.memory_manager = AsyncMock()
    service.memory_manager.load_context = AsyncMock(return_value=[])
    service.semantic_cache = AsyncMock()
    service.semantic_cache.get = AsyncMock(return_value="cached stream response")
    service._run_stream_postprocess = AsyncMock()

    chunks = [
        chunk
        async for chunk in service.process_message_stream(
            message="hello",
            conversation_id=None,
            user_id=None,
            context={},
            attachments=None,
            web_search=False,
        )
    ]

    assert chunks[-1].type == "done"
    assert service._run_stream_postprocess.call_count == 1
    assert service._run_stream_postprocess.await_count == 0
    assert mock_create_task.called


@pytest.mark.asyncio
@patch("src.services.chat_service.get_workflow")
@patch("src.services.chat_service.QualityAgent.should_run_async_review")
@patch("src.services.chat_service.QualityAgent.should_run_sync_review")
@patch("src.services.chat_service.asyncio.create_task")
@patch("src.services.chat_service.get_settings")
async def test_stream_high_risk_uses_sync_quality_review(
    mock_get_settings,
    mock_create_task,
    mock_should_sync,
    mock_should_async,
    mock_get_workflow,
):
    conv_id = uuid4()

    mock_get_settings.return_value = SimpleNamespace(
        ENABLE_SEMANTIC_CACHE=False,
        ENABLE_ASYNC_POSTPROCESS=True,
        ENABLE_SYNC_FIRST_TURN_SUMMARY=False,
        ENABLE_SYNC_QUALITY_REVIEW=True,
        SYNC_QUALITY_REVIEW_RISK_ONLY=True,
        ENABLE_ASYNC_QUALITY_REVIEW=True,
    )
    mock_should_sync.return_value = True
    mock_should_async.return_value = False
    mock_create_task.side_effect = lambda coro: (coro.close(), MagicMock())[1]
    mock_get_workflow.return_value = FakeWorkflow(
        [
            {
                "orchestrator": {
                    "intent": "complaint",
                    "worker_type": "faq_worker",
                    "sentiment": "angry",
                    "urgency": "high",
                }
            },
            {"faq_worker": {"worker_result": "请先确认订单信息。"}},
        ]
    )

    service = ChatService(db=AsyncMock())
    service._get_or_create_conversation = AsyncMock(return_value=SimpleNamespace(id=conv_id))
    service.msg_repo = AsyncMock()
    service.msg_repo.create = AsyncMock(side_effect=[SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())])
    service.memory_manager = AsyncMock()
    service.memory_manager.load_context = AsyncMock(return_value=[])
    service.semantic_cache = AsyncMock()
    service._run_stream_postprocess = AsyncMock()
    service._run_async_quality_review = AsyncMock()

    chunks = [
        chunk
        async for chunk in service.process_message_stream(
            message="我要投诉",
            conversation_id=None,
            user_id=None,
            context={},
            attachments=None,
            web_search=False,
        )
    ]

    assert chunks[-1].type == "done"
    assert service._run_async_quality_review.await_count == 1
    # only postprocess should be scheduled asynchronously in high-risk sync-review path
    assert mock_create_task.call_count == 1


@pytest.mark.asyncio
@patch("src.services.chat_service.get_workflow")
@patch("src.services.chat_service.QualityAgent.should_run_async_review")
@patch("src.services.chat_service.QualityAgent.should_run_sync_review")
@patch("src.services.chat_service.asyncio.create_task")
@patch("src.services.chat_service.get_settings")
async def test_stream_normal_uses_async_quality_review(
    mock_get_settings,
    mock_create_task,
    mock_should_sync,
    mock_should_async,
    mock_get_workflow,
):
    conv_id = uuid4()

    mock_get_settings.return_value = SimpleNamespace(
        ENABLE_SEMANTIC_CACHE=False,
        ENABLE_ASYNC_POSTPROCESS=True,
        ENABLE_SYNC_FIRST_TURN_SUMMARY=False,
        ENABLE_SYNC_QUALITY_REVIEW=True,
        SYNC_QUALITY_REVIEW_RISK_ONLY=True,
        ENABLE_ASYNC_QUALITY_REVIEW=True,
    )
    mock_should_sync.return_value = False
    mock_should_async.return_value = True
    mock_create_task.side_effect = lambda coro: (coro.close(), MagicMock())[1]
    mock_get_workflow.return_value = FakeWorkflow(
        [
            {
                "orchestrator": {
                    "intent": "faq",
                    "worker_type": "faq_worker",
                    "sentiment": "neutral",
                    "urgency": "low",
                }
            },
            {"faq_worker": {"worker_result": "这里是常规问题答案。"}},
        ]
    )

    service = ChatService(db=AsyncMock())
    service._get_or_create_conversation = AsyncMock(return_value=SimpleNamespace(id=conv_id))
    service.msg_repo = AsyncMock()
    service.msg_repo.create = AsyncMock(side_effect=[SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())])
    service.memory_manager = AsyncMock()
    service.memory_manager.load_context = AsyncMock(return_value=[])
    service.semantic_cache = AsyncMock()
    service._run_stream_postprocess = AsyncMock()
    service._run_async_quality_review = AsyncMock()

    chunks = [
        chunk
        async for chunk in service.process_message_stream(
            message="帮我查一下发票流程",
            conversation_id=None,
            user_id=None,
            context={},
            attachments=None,
            web_search=False,
        )
    ]

    assert chunks[-1].type == "done"
    assert service._run_async_quality_review.await_count == 0
    # async quality review + async postprocess
    assert mock_create_task.call_count == 2
