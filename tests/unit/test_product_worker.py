"""
Product Worker Agent 单元测试
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4


class TestProductWorkerInit:
    """Product Worker 初始化测试"""

    def test_product_worker_initialization(self):
        """测试 Product Worker 正确初始化"""
        from src.agents.workers.product_worker import ProductWorker

        worker = ProductWorker()

        assert worker.name == "product_worker"
        assert "产品" in worker.description

    def test_product_worker_has_search_tool(self):
        """测试 Product Worker 包含搜索工具"""
        from src.agents.workers.product_worker import ProductWorker

        worker = ProductWorker()
        tool_names = [t.name for t in worker.tools]

        assert "search_products" in tool_names


class TestProductWorkerHandle:
    """Product Worker handle 方法测试"""

    @pytest.mark.asyncio
    @patch("src.agents.workers.product_worker.create_react_agent")
    @patch("src.agents.workers.product_worker.get_llm_client")
    async def test_handle_with_product_id_context(self, mock_get_llm, mock_create_agent):
        """测试带 product_id 上下文的处理"""
        from src.agents.workers.product_worker import ProductWorker

        # Mock LLM client
        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        # Mock agent
        mock_agent = MagicMock()
        mock_result = {
            "messages": [MagicMock(content="iPhone 15 Pro 配置：A17芯片，256GB")]
        }
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = ProductWorker()
        context = {"product_id": "iphone-15-pro"}

        result = await worker.handle(
            user_input="这款手机有什么配置？",
            context=context,
            history=""
        )

        assert "iPhone" in result or "配置" in result
        assert mock_agent.ainvoke.called

    @pytest.mark.asyncio
    @patch("src.agents.workers.product_worker.create_react_agent")
    @patch("src.agents.workers.product_worker.get_llm_client")
    async def test_handle_with_history(self, mock_get_llm, mock_create_agent):
        """测试带对话历史的处理"""
        from src.agents.workers.product_worker import ProductWorker

        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        mock_agent = MagicMock()
        mock_result = {
            "messages": [MagicMock(content="推荐 iPhone 15")]
        }
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = ProductWorker()
        history = "用户：我想买手机\n客服：您有什么预算？\n用户：5000左右"

        result = await worker.handle(
            user_input="有什么推荐吗？",
            context={},
            history=history
        )

        assert result is not None
        assert mock_agent.ainvoke.called

    @pytest.mark.asyncio
    @patch("src.agents.workers.product_worker.create_react_agent")
    @patch("src.agents.workers.product_worker.get_llm_client")
    async def test_handle_with_retry_context(self, mock_get_llm, mock_create_agent):
        """测试重试上下文的处理"""
        from src.agents.workers.product_worker import ProductWorker

        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        mock_agent = MagicMock()
        mock_result = {
            "messages": [MagicMock(content="改进后的产品推荐")]
        }
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = ProductWorker()
        context = {
            "is_retry": True,
            "quality_reason": "缺少价格信息"
        }

        result = await worker.handle(
            user_input="请推荐一款手机",
            context=context,
            history=""
        )

        assert result is not None
        # 验证包含重试提示
        call_args = mock_agent.ainvoke.call_args
        prompt = call_args[0][0]["messages"][0][1]
        assert "上次回答存在问题" in prompt

    @pytest.mark.asyncio
    @patch("src.agents.workers.product_worker.create_react_agent")
    @patch("src.agents.workers.product_worker.get_llm_client")
    async def test_handle_empty_messages_fallback(self, mock_get_llm, mock_create_agent):
        """测试空消息的降级处理"""
        from src.agents.workers.product_worker import ProductWorker

        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        # 返回空消息
        mock_agent = MagicMock()
        mock_result = {"messages": []}
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = ProductWorker()
        result = await worker.handle("测试", {}, "")

        # 应该返回降级消息
        assert "抱歉" in result or "系统原因" in result or "无法" in result


class TestSearchProductsTool:
    """search_products 工具测试"""

    def test_search_products_tool_exists(self):
        """测试 search_products 工具存在"""
        from src.agents.workers.product_worker import search_products

        assert search_products.name == "search_products"
        assert "产品" in search_products.description

    @pytest.mark.asyncio
    @patch("src.rag.retriever.HybridRetriever")
    async def test_search_products_returns_results(self, mock_retriever_cls):
        """测试搜索产品返回结果"""
        from src.agents.workers.product_worker import search_products

        # Mock retriever
        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[
            {"content": "iPhone 15 Pro: A17芯片, 256GB, ¥8999"},
            {"content": "iPhone 15: A16芯片, 128GB, ¥5999"},
        ])
        mock_retriever_cls.return_value = mock_retriever

        result = await search_products.ainvoke("iPhone 15")

        assert "iPhone 15 Pro" in result
        assert "¥8999" in result

    @pytest.mark.asyncio
    @patch("src.rag.retriever.HybridRetriever")
    async def test_search_products_no_results(self, mock_retriever_cls):
        """测试无搜索结果"""
        from src.agents.workers.product_worker import search_products

        mock_retriever = MagicMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])
        mock_retriever_cls.return_value = mock_retriever

        result = await search_products.ainvoke("不存在的商品")

        assert "未查找到" in result or "暂无" in result

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要网络连接")
    async def test_search_products_exception_handling(self):
        """测试搜索异常处理"""
        from src.agents.workers.product_worker import search_products

        # 不 mock，让它抛出异常
        result = await search_products.ainvoke("测试")

        # 应该返回降级消息
        assert "暂不可用" in result or "知识库" in result


class TestProductWorkerMCP:
    """Product Worker MCP 增强测试"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要 MCP 服务器")
    @patch("src.agents.workers.product_worker.taobao_mcp_session")
    @patch("src.agents.workers.product_worker.create_react_agent")
    @patch("src.agents.workers.product_worker.get_llm_client")
    async def test_mcp_error_uses_basic_mode(self, mock_get_llm, mock_create_agent, mock_mcp_session):
        """测试 MCP 异常时回退到基础模式"""
        from src.agents.workers.product_worker import ProductWorker

        mock_client = MagicMock()
        mock_chat_model = MagicMock()
        mock_client.get_chat_model.return_value = mock_chat_model
        mock_get_llm.return_value = mock_client

        # Mock MCP session returns None
        mock_mcp = MagicMock()
        mock_mcp.__aenter__ = AsyncMock(return_value=(None, None))
        mock_mcp.__aexit__ = AsyncMock(return_value=None)
        mock_mcp_session.return_value = mock_mcp

        mock_agent = MagicMock()
        mock_result = {"messages": [MagicMock(content="正常回答")]}
        mock_agent.ainvoke = AsyncMock(return_value=mock_result)
        mock_create_agent.return_value = mock_agent

        worker = ProductWorker()
        result = await worker.handle("测试", {}, "")

        # 应该返回降级回答
        assert "正常回答" in result
