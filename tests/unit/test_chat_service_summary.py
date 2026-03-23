"""
ChatService 首轮摘要与命名测试
"""

from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from src.services.chat_service import ChatService


class TestChatServiceSummaryFinalize:
    @pytest.mark.asyncio
    async def test_finalize_first_turn_updates_title_summary_and_metadata(self):
        service = ChatService(db=AsyncMock())
        service.msg_repo = AsyncMock()
        service.conv_repo = AsyncMock()
        service.summary_agent = AsyncMock()

        conversation = SimpleNamespace(id=uuid4())
        latest = SimpleNamespace(id=conversation.id, title=None, metadata_=None)

        service.msg_repo.count_by_conversation.return_value = 2
        service.conv_repo.get_by_id.return_value = latest
        service.summary_agent.process = AsyncMock(
            return_value={
                "title": "退货进度查询",
                "summary": "用户咨询退货进度，客服已告知预计时效。",
                "key_points": ["订单号 ORD-1001", "状态：审核中"],
            }
        )
        service.conv_repo.update_by_id = AsyncMock()

        await service._finalize_first_turn_summary(
            conversation=conversation,
            user_message="请帮我查 ORD-1001 的退货进度",
            assistant_message="当前审核中，预计 1-3 个工作日完成。",
        )

        assert service.conv_repo.update_by_id.await_count == 1
        update_kwargs = service.conv_repo.update_by_id.await_args.kwargs
        assert update_kwargs["title"] == "退货进度查询"
        assert "退货进度" in update_kwargs["summary"]
        assert update_kwargs["metadata_"]["summary_key_points"] == ["订单号 ORD-1001", "状态：审核中"]

    @pytest.mark.asyncio
    async def test_finalize_first_turn_does_not_overwrite_existing_title(self):
        service = ChatService(db=AsyncMock())
        service.msg_repo = AsyncMock()
        service.conv_repo = AsyncMock()
        service.summary_agent = AsyncMock()

        conversation = SimpleNamespace(id=uuid4())
        latest = SimpleNamespace(id=conversation.id, title="手动命名会话", metadata_={"a": 1})

        service.msg_repo.count_by_conversation.return_value = 2
        service.conv_repo.get_by_id.return_value = latest
        service.summary_agent.process = AsyncMock(
            return_value={
                "title": "不应覆盖",
                "summary": "摘要保留",
                "key_points": ["关键点"],
            }
        )
        service.conv_repo.update_by_id = AsyncMock()

        await service._finalize_first_turn_summary(
            conversation=conversation,
            user_message="用户消息",
            assistant_message="客服回复",
        )

        update_kwargs = service.conv_repo.update_by_id.await_args.kwargs
        assert "title" not in update_kwargs
        assert update_kwargs["summary"] == "摘要保留"

    @pytest.mark.asyncio
    async def test_finalize_skips_when_not_first_turn(self):
        service = ChatService(db=AsyncMock())
        service.msg_repo = AsyncMock()
        service.conv_repo = AsyncMock()
        service.summary_agent = AsyncMock()

        conversation = SimpleNamespace(id=uuid4())
        service.msg_repo.count_by_conversation.return_value = 4
        service.conv_repo.update_by_id = AsyncMock()

        await service._finalize_first_turn_summary(
            conversation=conversation,
            user_message="用户消息",
            assistant_message="客服回复",
        )

        service.conv_repo.update_by_id.assert_not_called()
