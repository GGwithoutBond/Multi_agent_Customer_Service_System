import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFAQWorkerBaselineControls:
    @pytest.mark.asyncio
    @patch("src.agents.workers.faq_worker.get_llm_client")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_faq_worker_skips_retrieval_when_disabled(self, mock_retriever_cls, mock_get_llm):
        from src.agents.workers.faq_worker import FAQWorker

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="direct answer")
        mock_get_llm.return_value = mock_client

        worker = FAQWorker()
        result = await worker.handle(
            user_input="测试问题",
            context={"enable_retrieval": False},
            history="",
        )

        assert result == "direct answer"
        mock_retriever_cls.assert_not_called()
        prompt = mock_client.invoke.call_args[0][0][0].content
        assert "Knowledge retrieval disabled" in prompt

    @pytest.mark.asyncio
    @patch("src.agents.workers.faq_worker.get_llm_client")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_faq_worker_uses_vector_only_flags_for_rag_baseline(self, mock_retriever_cls, mock_get_llm):
        from src.agents.workers.faq_worker import FAQWorker

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[{"content": "价格 9999"}])
        mock_retriever_cls.return_value = mock_retriever

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="rag answer")
        mock_get_llm.return_value = mock_client

        worker = FAQWorker()
        await worker.handle(
            user_input="Apple iPhone 16 Pro Max 256GB 的价格是多少？",
            context={
                "enable_retrieval": True,
                "use_vector": True,
                "use_graph": False,
                "use_reranker": False,
            },
            history="",
        )

        mock_retriever.retrieve.assert_awaited_once_with(
            "Apple iPhone 16 Pro Max 256GB 的价格是多少？",
            top_k=5,
            use_vector=True,
            use_graph=False,
            use_reranker=False,
        )

    @pytest.mark.asyncio
    @patch("src.agents.workers.faq_worker.get_llm_client")
    @patch("src.rag.retriever.HybridRetriever")
    async def test_faq_worker_defaults_to_hybrid_retrieval(self, mock_retriever_cls, mock_get_llm):
        from src.agents.workers.faq_worker import FAQWorker

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[{"content": "价格 9999"}])
        mock_retriever_cls.return_value = mock_retriever

        mock_client = AsyncMock()
        mock_client.invoke = AsyncMock(return_value="hybrid answer")
        mock_get_llm.return_value = mock_client

        worker = FAQWorker()
        await worker.handle(
            user_input="Apple iPhone 16 Pro Max 256GB 的价格是多少？",
            context={},
            history="",
        )

        mock_retriever.retrieve.assert_awaited_once_with(
            "Apple iPhone 16 Pro Max 256GB 的价格是多少？",
            top_k=5,
            use_vector=True,
            use_graph=True,
            use_reranker=True,
        )


class TestGraphSearchNormalization:
    @pytest.mark.asyncio
    async def test_graph_search_normalizes_natural_language_queries(self):
        from src.rag.retriever import HybridRetriever

        async def side_effect(keyword, limit=10, node_types=None):
            if keyword == "Apple iPhone 16 Pro Max 256GB":
                return [
                    {
                        "name": "Apple iPhone 16 Pro Max 256GB",
                        "types": ["Product"],
                        "props": {"description": "价格 9999 元"},
                    }
                ]
            return []

        mock_graph_store = MagicMock()
        mock_graph_store.search_by_keyword = AsyncMock(side_effect=side_effect)

        retriever = HybridRetriever()
        retriever._graph_store = mock_graph_store

        queries = [
            "Apple iPhone 16 Pro Max 256GB",
            "Apple iPhone 16 Pro Max 256GB 多少钱",
            "请问 Apple iPhone 16 Pro Max 256GB 价格是多少",
        ]

        for query in queries:
            docs = await retriever._graph_search(query, top_k=3)
            assert docs
            assert docs[0]["id"] == "Apple iPhone 16 Pro Max 256GB"


class TestBaselineRunner:
    @pytest.mark.asyncio
    @patch("src.evaluation.baseline_runner.clear_retrieval_logs")
    @patch("src.evaluation.baseline_runner.get_retrieval_logs")
    @patch("src.evaluation.baseline_runner.get_workflow")
    @patch("src.evaluation.baseline_runner.FAQWorker")
    async def test_runner_generates_mode_results_and_summary(
        self,
        mock_worker_cls,
        mock_get_workflow,
        mock_get_retrieval_logs,
        mock_clear_logs,
        tmp_path,
    ):
        from src.evaluation.baseline_runner import BaselineRunner

        dataset_path = tmp_path / "dataset.json"
        dataset_path.write_text(
            json.dumps(
                [
                    {
                        "id": "case-1",
                        "query": "测试问题",
                        "expected_all_of": ["42"],
                        "expected_any_of": [],
                        "notes": "test",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        mock_worker = MagicMock()
        mock_worker.handle = AsyncMock(side_effect=["single 42", "rag 42"])
        mock_worker_cls.return_value = mock_worker

        mock_workflow = MagicMock()
        mock_workflow.ainvoke = AsyncMock(
            return_value={
                "worker_result": "workflow 42",
                "worker_type": "product_worker",
            }
        )
        mock_get_workflow.return_value = mock_workflow

        mock_get_retrieval_logs.side_effect = [
            [],
            [{"vector_hits": 5, "graph_hits": 0, "sources": ["vector"]}],
            [{"vector_hits": 3, "graph_hits": 1, "sources": ["vector", "graph"]}],
        ]

        runner = BaselineRunner(
            dataset_path=dataset_path,
            output_dir=tmp_path / "reports",
        )
        payload = await runner.run()

        assert [result["mode"] for result in payload["results"]] == [
            "single_agent",
            "rag_baseline",
            "current_system",
        ]
        assert payload["summary"]["single_agent"]["success_rate"] == 1.0
        assert payload["summary"]["rag_baseline"]["avg_vector_hits"] == 5
        assert payload["summary"]["current_system"]["avg_graph_hits"] == 1
        assert Path(payload["report_paths"]["json"]).exists()
        assert Path(payload["report_paths"]["markdown"]).exists()

        first_context = mock_worker.handle.await_args_list[0].kwargs["context"]
        second_context = mock_worker.handle.await_args_list[1].kwargs["context"]
        assert first_context == {"enable_retrieval": False}
        assert second_context == {
            "enable_retrieval": True,
            "use_vector": True,
            "use_graph": False,
            "use_reranker": False,
        }
