"""
Order Worker Agent 单元测试
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4


class TestOrderWorkerInit:
    """Order Worker 初始化测试"""

    def test_order_worker_initialization(self):
        """测试 Order Worker 正确初始化"""
        from src.agents.workers.order_worker import OrderWorker

        worker = OrderWorker()

        assert worker.name == "order_worker"
        assert "订单" in worker.description
        assert len(worker.tools) >= 3  # query_order, query_user_orders, process_return

    def test_order_worker_has_tools(self):
        """测试 Order Worker 包含必要的工具"""
        from src.agents.workers.order_worker import OrderWorker

        worker = OrderWorker()
        tool_names = [t.name for t in worker.tools]

        assert "query_order" in tool_names
        assert "query_user_orders" in tool_names
        assert "process_return" in tool_names


class TestOrderWorkerHandle:
    """Order Worker handle 方法测试"""

    @pytest.mark.asyncio
    @patch("src.agents.workers.order_worker.create_react_agent")
    @patch("src.agents.workers.order_worker.get_llm_client")
    async def test_handle_with_order_id_context(self, mock_get_llm, mock_create_agent):
        """测试带 order_id 上下文的处理"""
        from src.agents.workers.order_worker import OrderWorker

        # Mock LLM client
        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        # Mock agent
        mock_agent = MagicMock()
        mock_result = {
            "messages": [MagicMock(content="订单已发货，预计明天送达")]
        }
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = OrderWorker()
        context = {"order_id": "12345"}

        result = await worker.handle(
            user_input="我的订单到哪里了？",
            context=context,
            history=""
        )

        assert "订单" in result
        assert mock_agent.ainvoke.called

    @pytest.mark.asyncio
    @patch("src.agents.workers.order_worker.create_react_agent")
    @patch("src.agents.workers.order_worker.get_llm_client")
    async def test_handle_with_history(self, mock_get_llm, mock_create_agent):
        """测试带对话历史的处理"""
        from src.agents.workers.order_worker import OrderWorker

        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        mock_agent = MagicMock()
        mock_result = {
            "messages": [MagicMock(content="退款处理中")]
        }
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = OrderWorker()
        history = "用户：我想退货\n客服：请问订单号是多少？\n用户：12345"

        result = await worker.handle(
            user_input="还没处理吗？",
            context={},
            history=history
        )

        assert result is not None
        # 验证 agent 被调用
        call_args = mock_agent.ainvoke.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    @patch("src.agents.workers.order_worker.create_react_agent")
    @patch("src.agents.workers.order_worker.get_llm_client")
    async def test_handle_with_retry_context(self, mock_get_llm, mock_create_agent):
        """测试重试上下文的处理"""
        from src.agents.workers.order_worker import OrderWorker

        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        mock_agent = MagicMock()
        mock_result = {
            "messages": [MagicMock(content="改进后的回答")]
        }
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = OrderWorker()
        context = {
            "is_retry": True,
            "quality_reason": "回答不够详细"
        }

        result = await worker.handle(
            user_input="请详细说明",
            context=context,
            history=""
        )

        assert result is not None
        # 验证包含重试提示
        call_args = mock_agent.ainvoke.call_args
        prompt = call_args[0][0]["messages"][0][1]
        assert "上次回答存在问题" in prompt

    @pytest.mark.asyncio
    @patch("src.agents.workers.order_worker.create_react_agent")
    @patch("src.agents.workers.order_worker.get_llm_client")
    async def test_handle_empty_messages_fallback(self, mock_get_llm, mock_create_agent):
        """测试空消息的降级处理"""
        from src.agents.workers.order_worker import OrderWorker

        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        # 返回空消息
        mock_agent = MagicMock()
        mock_result = {"messages": []}
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = OrderWorker()
        result = await worker.handle("测试", {}, "")

        # 应该返回降级消息
        assert "抱歉" in result or "系统原因" in result


class TestOrderWorkerTools:
    """Order Worker 工具测试"""

    def test_query_order_tool_exists(self):
        """测试 query_order 工具存在"""
        from src.tools.database_tool import query_order

        assert query_order.name == "query_order"
        assert "订单" in query_order.description

    def test_query_user_orders_tool_exists(self):
        """测试 query_user_orders 工具存在"""
        from src.tools.database_tool import query_user_orders

        assert query_user_orders.name == "query_user_orders"

    def test_process_return_tool_exists(self):
        """测试 process_return 工具存在"""
        from src.tools.database_tool import process_return

        assert process_return.name == "process_return"


class TestOrderWorkerMCP:
    """Order Worker MCP 增强测试"""

    @pytest.mark.asyncio
    @patch("src.agents.workers.order_worker.Settings")
    @patch("src.agents.workers.order_worker.create_react_agent")
    @patch("src.agents.workers.order_worker.get_llm_client")
    async def test_mcp_disabled_uses_basic_mode(self, mock_get_llm, mock_create_agent, mock_settings):
        """测试 MCP 禁用时使用基础模式"""
        from src.agents.workers.order_worker import OrderWorker

        # Mock settings
        mock_settings_instance = MagicMock()
        mock_settings_instance.MCP_ENABLED = False
        mock_settings.return_value = mock_settings_instance

        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        mock_agent = MagicMock()
        mock_result = {"messages": [MagicMock(content="正常回答")]}
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = OrderWorker()
        result = await worker.handle("测试", {}, "")

        assert "正常回答" in result

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要 MCP 服务器")
    @patch("src.agents.workers.order_worker.taobao_mcp_session")
    @patch("src.agents.workers.order_worker.Settings")
    @patch("src.agents.workers.order_worker.create_react_agent")
    @patch("src.agents.workers.order_worker.get_llm_client")
    async def test_mcp_enabled_tries_enhance_mode(self, mock_get_llm, mock_create_agent, mock_settings, mock_mcp_session):
        """测试 MCP 启用时尝试增强模式"""
        from src.agents.workers.order_worker import OrderWorker

        # Mock settings
        mock_settings_instance = MagicMock()
        mock_settings_instance.MCP_ENABLED = True
        mock_settings.return_value = mock_settings_instance

        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        # Mock MCP session
        mock_mcp = MagicMock()
        mock_mcp.__aenter__ = AsyncMock(return_value=(None, None))
        mock_mcp.__aexit__ = AsyncMock(return_value=None)
        mock_mcp_session.return_value = mock_mcp

        mock_agent = MagicMock()
        mock_result = {"messages": [MagicMock(content="MCP增强回答")]}
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = OrderWorker()
        result = await worker.handle("测试", {}, "")

        # 应该返回回答
        assert result is not None
