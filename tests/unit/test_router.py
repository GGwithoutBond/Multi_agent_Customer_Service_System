"""
Agent 路由决策测试
测试意图识别、Worker 路由、情感分析功能
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.agents.orchestrator.router import (
    route_decision,
    classify_intent,
    get_worker_type,
    _extract_json_from_response,
    INTENT_WORKER_MAP,
)


class TestIntentRouting:
    """意图路由测试"""

    @pytest.mark.parametrize("intent,expected_worker", [
        ("faq", "faq_worker"),
        ("order", "order_worker"),
        ("product", "product_worker"),
        ("complaint", "complaint_worker"),
        ("human", "human_worker"),
        ("greeting", "faq_worker"),
        ("unknown", "faq_worker"),
    ])
    def test_intent_to_worker_mapping(self, intent, expected_worker):
        """测试意图到 Worker 的映射"""
        assert get_worker_type(intent) == expected_worker

    def test_unknown_intent_defaults_to_faq(self):
        """测试未知意图默认路由到 faq_worker"""
        assert get_worker_type("invalid_intent") == "faq_worker"


class TestRouteDecision:
    """路由决策测试"""

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_route_faq_intent(self, mock_get_client):
        """测试 FAQ 意图识别"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value='{"intent": "faq", "worker_type": "faq", "sentiment": "neutral", "urgency": "medium"}')
        mock_get_client.return_value = mock_client

        result = await route_decision("你们的退货政策是什么？")

        assert result["intent"] == "faq"
        assert result["worker_type"] == "faq_worker"
        assert result["sentiment"] == "neutral"

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_route_order_intent(self, mock_get_client):
        """测试订单意图识别"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value='{"intent": "order", "worker_type": "order", "sentiment": "neutral", "urgency": "medium"}')
        mock_get_client.return_value = mock_client

        result = await route_decision("我的订单到哪里了？")

        assert result["intent"] == "order"
        assert result["worker_type"] == "order_worker"

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_route_product_intent(self, mock_get_client):
        """测试商品意图识别"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value='{"intent": "product", "worker_type": "product", "sentiment": "positive", "urgency": "low"}')
        mock_get_client.return_value = mock_client

        result = await route_decision("这款手机有什么配置？")

        assert result["intent"] == "product"
        assert result["worker_type"] == "product_worker"

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_route_complaint_intent(self, mock_get_client):
        """测试投诉意图识别"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value='{"intent": "complaint", "worker_type": "complaint", "sentiment": "negative", "urgency": "high"}')
        mock_get_client.return_value = mock_client

        result = await route_decision("产品质量太差了，我要投诉")

        assert result["intent"] == "complaint"
        assert result["worker_type"] == "complaint_worker"


class TestSentimentAnalysis:
    """情感分析测试"""

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_angry_sentiment_escalation(self, mock_get_client):
        """测试愤怒情绪自动升级到人工"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value='{"intent": "complaint", "worker_type": "complaint", "sentiment": "angry", "urgency": "high"}')
        mock_get_client.return_value = mock_client

        result = await route_decision("垃圾产品！再也不买了！退款！")

        # angry + complaint + high 应该升级到 human_worker
        assert result["worker_type"] == "human_worker"
        assert result["urgency"] == "critical"

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_frustrated_critical_escalation(self, mock_get_client):
        """测试沮丧情绪 + critical 紧急度升级"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value='{"intent": "faq", "worker_type": "faq", "sentiment": "frustrated", "urgency": "critical"}')
        mock_get_client.return_value = mock_client

        result = await route_decision("这个问题到底能不能解决？太失望了！")

        # frustrated + critical 应该升级
        assert result["worker_type"] == "human_worker"

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_angry_not_escalate_when_low_urgency(self, mock_get_client):
        """测试愤怒但低紧急度不升级"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value='{"intent": "faq", "worker_type": "faq", "sentiment": "angry", "urgency": "low"}')
        mock_get_client.return_value = mock_client

        result = await route_decision("能不能快点回复")

        # angry + low urgency 不升级到人工，但会路由到 complaint_worker
        assert result["worker_type"] == "complaint_worker"


class TestRouteDecisionEdgeCases:
    """路由决策边界情况测试"""

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_invalid_sentiment_defaults_neutral(self, mock_get_client):
        """测试无效情感值默认 neutral"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value='{"intent": "faq", "worker_type": "faq", "sentiment": "happy", "urgency": "medium"}')
        mock_get_client.return_value = mock_client

        result = await route_decision("测试")

        assert result["sentiment"] == "neutral"

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_invalid_urgency_defaults_medium(self, mock_get_client):
        """测试无效紧急度默认 medium"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value='{"intent": "faq", "worker_type": "faq", "sentiment": "neutral", "urgency": "urgent"}')
        mock_get_client.return_value = mock_client

        result = await route_decision("测试")

        assert result["urgency"] == "medium"

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_json_parse_failure_fallback(self, mock_get_client):
        """测试 JSON 解析失败降级"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="无效的文本响应")
        mock_get_client.return_value = mock_client

        result = await route_decision("测试")

        # 应该降级到简单分类
        assert result["worker_type"] == "faq_worker"
        assert "reasoning" in result

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_llm_exception_safe_default(self, mock_get_client):
        """测试 LLM 异常时返回安全默认值"""
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(side_effect=Exception("API Error"))
        mock_get_client.return_value = mock_client

        result = await route_decision("测试")

        # 应该返回安全默认值
        assert result["intent"] == "unknown"
        assert result["worker_type"] == "faq_worker"
        assert "异常" in result.get("reasoning", "")


class TestJsonExtraction:
    """JSON 提取测试"""

    @pytest.mark.parametrize("text,expected", [
        ('{"intent": "faq"}', {"intent": "faq"}),
        ('{"intent": "order", "sentiment": "neutral"}', {"intent": "order", "sentiment": "neutral"}),
        ('```json\n{"intent": "product"}\n```', {"intent": "product"}),
        ("not json", None),
        ("", None),
    ])
    def test_extract_json_from_response(self, text, expected):
        """测试 JSON 提取"""
        result = _extract_json_from_response(text)
        assert result == expected
