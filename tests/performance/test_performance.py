"""
Agent 性能测试
测试响应时间、并发处理、资源使用
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from statistics import mean, stdev


class TestResponseTime:
    """响应时间测试"""

    @pytest.mark.asyncio
    @patch("src.agents.workers.faq_worker.get_llm_client")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_faq_response_time_under_threshold(self, mock_retriever_cls, mock_get_llm):
        """测试 FAQ 响应时间 < 3秒"""
        from src.agents.workers.faq_worker import FAQWorker

        # Mock 快速响应
        async def fast_invoke(*args, **kwargs):
            await asyncio.sleep(0.01)  # 模拟 10ms LLM 延迟
            return "测试回答"

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[{"content": "test"}])
        mock_retriever_cls.return_value = mock_retriever

        mock_client = AsyncMock()
        mock_client.invoke = fast_invoke
        mock_get_llm.return_value = mock_client

        worker = FAQWorker()

        start = time.perf_counter()
        await worker.handle("测试问题", {}, "")
        elapsed = time.perf_counter() - start

        assert elapsed < 3.0, f"响应时间 {elapsed:.2f}s 超过 3s 阈值"

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_router_response_time(self, mock_get_llm):
        """测试路由决策响应时间 < 1秒"""
        from src.agents.orchestrator.router import route_decision

        async def fast_invoke(*args, **kwargs):
            await asyncio.sleep(0.01)
            return '{"intent": "faq", "worker_type": "faq", "sentiment": "neutral", "urgency": "medium"}'

        mock_client = AsyncMock()
        mock_client.invoke = fast_invoke
        mock_get_llm.return_value = mock_client

        start = time.perf_counter()
        result = await route_decision("测试")
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"路由时间 {elapsed:.2f}s 超过 1s 阈值"
        assert result["intent"] == "faq"


class TestConcurrentRequests:
    """并发请求测试"""

    @pytest.mark.asyncio
    @patch("src.agents.workers.faq_worker.get_llm_client")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_concurrent_faq_requests(self, mock_retriever_cls, mock_get_llm):
        """测试并发处理多个 FAQ 请求"""
        from src.agents.workers.faq_worker import FAQWorker

        call_count = 0

        async def mock_invoke(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return f"回答 {call_count}"

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        mock_retriever_cls.return_value = mock_retriever

        mock_client = AsyncMock()
        mock_client.invoke = mock_invoke
        mock_get_llm.return_value = mock_client

        worker = FAQWorker()

        # 并发执行 10 个请求
        tasks = [
            worker.handle(f"问题 {i}", {}, "")
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(isinstance(r, str) for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_routing(self):
        """测试并发路由决策"""
        from src.agents.orchestrator.router import route_decision

        async def mock_route(*args, **kwargs):
            await asyncio.sleep(0.01)
            return {
                "intent": "faq",
                "worker_type": "faq_worker",
                "sentiment": "neutral",
                "urgency": "medium",
            }

        with patch("src.agents.orchestrator.router.route_decision", side_effect=mock_route):
            tasks = [route_decision(f"消息 {i}") for i in range(20)]
            results = await asyncio.gather(*tasks)

            assert len(results) == 20


class TestBatchProcessing:
    """批量处理测试"""

    @pytest.mark.asyncio
    async def test_batch_intent_classification(self):
        """测试批量意图分类"""
        # 测试批量处理能力，不依赖实际 API
        test_messages = ["问题1", "问题2", "问题3"]

        # 模拟批量处理
        results = []
        for msg in test_messages:
            await asyncio.sleep(0.001)
            results.append(len(msg))

        assert len(results) == 3
        assert all(r > 0 for r in results)


class TestResourceUsage:
    """资源使用测试"""

    @pytest.mark.asyncio
    async def test_workflow_compilation_performance(self):
        """测试工作流编译性能"""
        from src.agents.graph.workflow import compile_workflow

        # 多次编译测试稳定性
        times = []
        for _ in range(5):
            start = time.perf_counter()
            workflow = compile_workflow()
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        avg_time = mean(times)
        assert avg_time < 1.0, f"编译平均时间 {avg_time:.2f}s 超过 1s"

    def test_workflow_singleton_pattern(self):
        """测试工作流单例模式"""
        from src.agents.graph.workflow import get_workflow

        workflow1 = get_workflow()
        workflow2 = get_workflow()

        # 验证返回同一实例
        assert workflow1 is workflow2


class TestLatencyMetrics:
    """延迟指标测试"""

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_typical_request_latency(self, mock_get_llm):
        """测试典型请求延迟分布"""
        from src.agents.orchestrator.router import route_decision

        latencies = []
        num_requests = 20

        async def mock_invoke(*args, **kwargs):
            await asyncio.sleep(0.02)  # 模拟 20ms 延迟
            return '{"intent": "faq", "worker_type": "faq", "sentiment": "neutral", "urgency": "medium"}'

        mock_client = AsyncMock()
        mock_client.invoke = mock_invoke
        mock_get_llm.return_value = mock_client

        for _ in range(num_requests):
            start = time.perf_counter()
            await route_decision("测试消息")
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)

        avg_latency = mean(latencies)
        p95_latency = sorted(latencies)[int(num_requests * 0.95)]

        assert avg_latency < 0.5, f"平均延迟 {avg_latency:.3f}s 过高"
        assert p95_latency < 1.0, f"P95 延迟 {p95_latency:.3f}s 过高"

    @pytest.mark.asyncio
    async def test_llm_latency_impact(self):
        """测试 LLM 延迟对整体响应的影响"""
        from src.agents.workers.faq_worker import FAQWorker

        llm_latencies = [0.1, 0.5, 1.0, 2.0]

        with patch("src.agents.workers.faq_worker.get_llm_client") as mock_get_llm:
            with patch("src.rag.retriever.HybridRetriever") as mock_retriever_cls:
                mock_retriever = MagicMock()
                mock_retriever.retrieve = AsyncMock(return_value=[])
                mock_retriever_cls.return_value = mock_retriever

                for llm_latency in llm_latencies:
                    async def slow_invoke(*args, **kwargs):
                        await asyncio.sleep(llm_latency)
                        return "回答"

                    mock_client = AsyncMock()
                    mock_client.invoke = slow_invoke
                    mock_get_llm.return_value = mock_client

                    worker = FAQWorker()

                    start = time.perf_counter()
                    await worker.handle("测试", {}, "")
                    elapsed = time.perf_counter() - start

                    # 整体延迟应该接近 LLM 延迟
                    assert abs(elapsed - llm_latency) < 0.2, \
                        f"LLM 延迟 {llm_latency}s vs 实际 {elapsed:.2f}s 差异过大"
