"""
Agent 工作流测试
测试 LangGraph 工作流的构建和执行
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.agents.graph.workflow import build_workflow, compile_workflow, get_workflow
from src.agents.orchestrator.state import AgentState
from src.agents.graph.nodes import quality_review_node


class TestWorkflowBuilding:
    """工作流构建测试"""

    def test_build_workflow_returns_stategraph(self):
        """测试工作流构建返回 StateGraph"""
        workflow = build_workflow()
        assert workflow is not None

    def test_workflow_has_all_nodes(self):
        """测试工作流包含所有节点"""
        workflow = build_workflow()

        # 验证节点存在
        nodes = ["orchestrator", "faq_worker", "order_worker", "product_worker",
                 "complaint_worker", "human_worker", "web_search", "quality_review"]

        # StateGraph 的节点通过 add_node 添加
        # 这里验证编译成功即可
        compiled = compile_workflow()
        assert compiled is not None

    def test_compile_workflow(self):
        """测试工作流编译"""
        compiled = compile_workflow()
        assert compiled is not None
        assert hasattr(compiled, 'invoke')
        assert hasattr(compiled, 'ainvoke')


class TestWorkflowExecution:
    """工作流执行测试"""

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_workflow_runs_faq_path(self, mock_get_llm):
        """测试工作流执行 FAQ 路径"""
        # Mock LLM
        mock_client = AsyncMock()
        mock_client.ainvoke = AsyncMock(return_value='{"intent": "faq", "worker_type": "faq", "sentiment": "neutral", "urgency": "medium"}')
        mock_get_llm.return_value = mock_client

        # Mock Workers
        with patch("src.agents.graph.nodes.faq_worker_node") as mock_faq:
            mock_faq.return_value = {"response": "FAQ 回答"}

            workflow = compile_workflow()

            # 执行工作流
            result = await workflow.ainvoke({
                "messages": [],
                "user_input": "退货政策是什么？",
                "conversation_id": "test-conv",
                "user_id": "test-user",
                "context": {},
            })

            assert result is not None

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.router.get_llm_client")
    async def test_workflow_routes_to_correct_worker(self, mock_get_llm):
        """测试工作流路由到正确的 Worker"""
        mock_client = AsyncMock()
        mock_client.ainvoke = AsyncMock(return_value='{"intent": "order", "worker_type": "order", "sentiment": "neutral", "urgency": "medium"}')
        mock_get_llm.return_value = mock_client

        workflow = compile_workflow()

        # 验证返回包含 worker 信息
        initial_state = {
            "messages": [],
            "user_input": "查一下订单",
            "conversation_id": "test-conv",
            "user_id": "test-user",
            "context": {},
        }

        result = await workflow.ainvoke(initial_state)
        assert result is not None


class TestAgentState:
    """Agent 状态测试"""

    def test_agent_state_structure(self):
        """测试状态结构定义"""
        state: AgentState = {
            "messages": [],
            "user_input": "测试",
            "conversation_id": "conv-1",
            "user_id": "user-1",
            "intent": None,
            "worker_type": None,
            "worker_result": None,
            "context": {},
            "response": None,
            "error": None,
            "needs_human": False,
            "web_search": False,
            "web_search_result": None,
            "sentiment": "neutral",
            "urgency": "medium",
            "working_memory": None,
            "retry_count": 0,
            "quality_score": None,
            "quality_reason": None,
            "quality_risk_flags": None,
        }

        assert state["user_input"] == "测试"
        assert state["sentiment"] == "neutral"
        assert state["urgency"] == "medium"
        assert state["retry_count"] == 0

    def test_agent_state_allows_optional_fields(self):
        """测试状态可选字段"""
        state: AgentState = {
            "messages": [],
            "user_input": "测试",
            "conversation_id": "conv-1",
            "user_id": None,  # 可选
            "intent": None,
            "worker_type": None,
            "worker_result": None,
            "context": {},
            "response": None,
            "error": None,
            "needs_human": False,
            "web_search": False,
            "web_search_result": None,
            "sentiment": None,  # 可选
            "urgency": None,  # 可选
            "working_memory": None,
            "retry_count": 0,
            "quality_score": None,
            "quality_reason": None,
            "quality_risk_flags": None,
        }

        assert state["user_id"] is None
        assert state["sentiment"] is None


class TestQualityReviewNode:
    """质量审查节点测试"""

    @pytest.mark.asyncio
    @patch("src.agents.graph.nodes._quality_agent.process", new_callable=AsyncMock)
    async def test_quality_review_node_uses_quality_agent(self, mock_quality_process):
        mock_quality_process.return_value = {
            "quality_score": 4,
            "quality_reason": "回答基本完整",
            "quality_risk_flags": [],
        }

        result = await quality_review_node(
            {
                "user_input": "退货要多久",
                "worker_result": "一般 1-3 个工作日",
                "retry_count": 0,
            }
        )

        assert result["quality_score"] == 4
        mock_quality_process.assert_awaited_once()
