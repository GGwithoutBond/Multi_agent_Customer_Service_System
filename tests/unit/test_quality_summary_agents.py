"""
SummaryAgent / QualityAgent 单元测试
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestQualityAgent:
    @pytest.mark.asyncio
    @patch("src.agents.quality_agent.get_llm_client")
    async def test_quality_agent_low_score_triggers_retry(self, mock_get_llm):
        from src.agents.quality_agent import QualityAgent

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(
            return_value='{"score": 2, "reason": "答非所问", "risk_flags": ["missing_actionability"]}'
        )
        mock_get_llm.return_value = mock_client

        agent = QualityAgent()
        result = await agent.process(
            {
                "user_input": "怎么退货",
                "worker_result": "请关注天气",
                "retry_count": 0,
            }
        )

        assert result["quality_score"] == 2
        assert result["retry_count"] == 1
        assert result["quality_reason"] == "答非所问"
        assert result["quality_risk_flags"] == ["missing_actionability"]

    @pytest.mark.asyncio
    @patch("src.agents.quality_agent.get_llm_client")
    async def test_quality_agent_invalid_json_fallback(self, mock_get_llm):
        from src.agents.quality_agent import QualityAgent

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="not-json")
        mock_get_llm.return_value = mock_client

        agent = QualityAgent()
        result = await agent.process(
            {
                "user_input": "测试问题",
                "worker_result": "测试回答",
                "retry_count": 0,
            }
        )

        assert result["quality_score"] == 5
        assert result.get("retry_count", 0) == 0


class TestSummaryAgent:
    @pytest.mark.asyncio
    @patch("src.agents.summary_agent.get_llm_client")
    async def test_summary_agent_returns_structured_output(self, mock_get_llm):
        from src.agents.summary_agent import SummaryAgent

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(
            return_value=(
                '{"title":"退货进度确认","summary":"用户咨询退货进度，客服给出处理节点。",'
                '"key_points":["订单号 ORD-1001","状态：审核中"]}'
            )
        )
        mock_get_llm.return_value = mock_client

        agent = SummaryAgent()
        result = await agent.process(
            {
                "user_message": "请帮我查 ORD-1001 的退货进度",
                "assistant_message": "当前处于审核中，预计 1-3 个工作日完成。",
            }
        )

        assert result["title"] == "退货进度确认"
        assert "退货进度" in result["summary"]
        assert "订单号 ORD-1001" in result["key_points"]

    @pytest.mark.asyncio
    @patch("src.agents.summary_agent.get_llm_client")
    async def test_summary_agent_fallback_when_invalid_json(self, mock_get_llm):
        from src.agents.summary_agent import SummaryAgent

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="invalid-json")
        mock_get_llm.return_value = mock_client

        agent = SummaryAgent()
        user_message = "我想了解退货规则和流程"
        result = await agent.process(
            {
                "user_message": user_message,
                "assistant_message": "可以在订单页发起退货，按步骤提交即可。",
            }
        )

        assert result["title"]
        assert "用户诉求" in result["summary"]
        assert len(result["key_points"]) >= 1
