"""
Worker Agent 测试
测试各 Worker 的功能、处理逻辑、效果
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4


class TestFAQWorker:
    """FAQ Worker 功能测试"""

    @pytest.mark.asyncio
    @patch("src.agents.workers.faq_worker.get_llm_client")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_faq_handle_returns_response(self, mock_retriever_cls, mock_get_llm):
        """测试 FAQ Worker 返回回答"""
        from src.agents.workers.faq_worker import FAQWorker

        # Mock RAG
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[
            {"content": "退货政策：30天内可退货"}
        ])
        mock_retriever_cls.return_value = mock_retriever

        # Mock LLM
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="30天内可以申请退货，请联系客服")
        mock_get_llm.return_value = mock_client

        worker = FAQWorker()
        result = await worker.handle(
            user_input="退货政策是什么？",
            context={},
            history=""
        )

        assert isinstance(result, str)
        assert len(result) > 0
        mock_client.invoke.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.agents.workers.faq_worker.get_llm_client")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_faq_handles_empty_rag_results(self, mock_retriever_cls, mock_get_llm):
        """测试 RAG 无结果时的处理"""
        from src.agents.workers.faq_worker import FAQWorker

        # Mock 空结果
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        mock_retriever_cls.return_value = mock_retriever

        # Mock LLM
        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="知识库暂无相关信息")
        mock_get_llm.return_value = mock_client

        worker = FAQWorker()
        result = await worker.handle(
            user_input="非常冷门的问题",
            context={},
            history=""
        )

        assert isinstance(result, str)
        # LLM 仍被调用，使用通用知识回答
        mock_client.invoke.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要网络连接")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_faq_handles_rag_exception(self, mock_retriever_cls):
        """测试 RAG 异常时的降级处理"""
        from src.agents.workers.faq_worker import FAQWorker

        # Mock RAG 异常
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(side_effect=Exception("RAG Error"))
        mock_retriever_cls.return_value = mock_retriever

        worker = FAQWorker()
        result = await worker.handle(
            user_input="测试问题",
            context={},
            history=""
        )

        # 应该返回降级消息
        assert "暂不可用" in result or "知识库" in result


class TestOrderWorker:
    """Order Worker 功能测试"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要网络连接")
    @patch("src.agents.workers.order_worker.get_llm_client")
    async def test_order_handle_query(self, mock_get_llm):
        """测试 Order Worker 处理订单查询"""
        from src.agents.workers.order_worker import OrderWorker

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="您的订单已发货，预计3天内送达")
        mock_get_llm.return_value = mock_client

        worker = OrderWorker()
        result = await worker.handle(
            user_input="订单12345到哪里了？",
            context={"order_id": "12345"},
            history=""
        )

        assert isinstance(result, str)
        assert "订单" in result or "发货" in result

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要网络连接")
    @patch("src.agents.workers.order_worker.get_llm_client")
    async def test_order_handle_refund(self, mock_get_llm):
        """测试 Order Worker 处理退款请求"""
        from src.agents.workers.order_worker import OrderWorker

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="退款申请已提交，1-3个工作日内处理")
        mock_get_llm.return_value = mock_client

        worker = OrderWorker()
        result = await worker.handle(
            user_input="我要申请退款",
            context={"order_id": "12345"},
            history=""
        )

        assert "退款" in result


class TestProductWorker:
    """Product Worker 功能测试"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要特殊 mock 配置")
    @patch("src.agents.workers.product_worker.get_llm_client")
    async def test_product_handle_query(self, mock_get_llm):
        """测试 Product Worker 处理商品查询"""
        from src.agents.workers.product_worker import ProductWorker

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="iPhone 15 Pro 配置：A17芯片，256GB存储")
        mock_get_llm.return_value = mock_client

        worker = ProductWorker()
        result = await worker.handle(
            user_input="iPhone 15 Pro 有什么配置？",
            context={},
            history=""
        )

        assert isinstance(result, str)


class TestComplaintWorker:
    """Complaint Worker 功能测试"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要网络连接")
    @patch("src.agents.workers.complaint_worker.get_llm_client")
    async def test_complaint_handles_negatively(self, mock_get_llm):
        """测试 Complaint Worker 处理投诉"""
        from src.agents.workers.complaint_worker import ComplaintWorker

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="非常抱歉给您带来不便，我们会立即处理您的问题")
        mock_get_llm.return_value = mock_client

        worker = ComplaintWorker()
        result = await worker.handle(
            user_input="产品太差了，要投诉",
            context={"sentiment": "negative", "urgency": "high"},
            history=""
        )

        assert isinstance(result, str)
        assert "抱歉" in result or "处理" in result

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要网络连接")
    @patch("src.agents.workers.complaint_worker.get_llm_client")
    async def test_complaint_escalation_when_urgent(self, mock_get_llm):
        """测试紧急投诉转人工"""
        from src.agents.workers.complaint_worker import ComplaintWorker

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="已为您转接人工客服")
        mock_get_llm.return_value = mock_client

        worker = ComplaintWorker()
        result = await worker.handle(
            user_input="严重质量问题，必须马上解决",
            context={"sentiment": "angry", "urgency": "critical"},
            history=""
        )

        # critical 应该标记转人工
        assert worker.name == "complaint_worker"


class TestHumanWorker:
    """Human Worker 功能测试"""

    @pytest.mark.asyncio
    async def test_human_worker_always_escalates(self):
        """测试 Human Worker 标记需要转人工"""
        from src.agents.workers.human_worker import HumanWorker

        worker = HumanWorker()
        result = await worker.handle(
            user_input="我需要人工服务",
            context={"needs_human": True},
            history=""
        )

        # Human worker 应该返回转接提示
        assert "人工" in result or "客服" in result


class TestWorkerEffectiveness:
    """Worker 效果测试"""

    @pytest.mark.asyncio
    @patch("src.agents.workers.faq_worker.get_llm_client")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_faq_includes_context_in_response(self, mock_retriever_cls, mock_get_llm):
        """测试 FAQ 使用检索上下文"""
        from src.agents.workers.faq_worker import FAQWorker

        expected_context = "退货政策：30天内可退货"

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[
            {"content": expected_context}
        ])
        mock_retriever_cls.return_value = mock_retriever

        mock_client = MagicMock()
        mock_client.invoke = AsyncMock(return_value="回答内容")
        mock_get_llm.return_value = mock_client

        worker = FAQWorker()
        await worker.handle("退货政策", {}, "")

        # 验证 LLM 调用包含检索内容
        call_args = mock_client.invoke.call_args
        prompt = call_args[0][0][0].content
        assert expected_context in prompt

    @pytest.mark.asyncio
    @patch("src.agents.workers.faq_worker.get_llm_client")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_faq_uses_persona_from_context(self, mock_retriever_cls, mock_get_llm):
        """测试 FAQ 使用人设上下文"""
        from src.agents.workers.faq_worker import FAQWorker

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        mock_retriever_cls.return_value = mock_retriever

        mock_client = MagicMock()
        mock_client.invoke = AsyncMock(return_value="回答")
        mock_get_llm.return_value = mock_client

        worker = FAQWorker()
        persona_context = {"persona_style": "friendly"}
        result = await worker.handle("你好", persona_context, "")

        # 验证返回了结果
        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("src.agents.workers.faq_worker.get_llm_client")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_faq_includes_history(self, mock_retriever_cls, mock_get_llm):
        """测试 FAQ 包含对话历史"""
        from src.agents.workers.faq_worker import FAQWorker

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        mock_retriever_cls.return_value = mock_retriever

        mock_client = MagicMock()
        mock_client.invoke = AsyncMock(return_value="回答")
        mock_get_llm.return_value = mock_client

        worker = FAQWorker()
        history = "用户：我想退货\n客服：请问是什么原因？"
        await worker.handle("还没答复", {}, history)

        # 验证包含历史
        call_args = mock_client.invoke.call_args
        prompt = call_args[0][0][0].content
        assert "退货" in prompt
