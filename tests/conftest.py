"""
Agent 测试配置和 Fixtures
"""

import asyncio
import os
import sys
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# 设置测试环境
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "error")

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_llm_response():
    """创建指定响应的 Mock LLM 客户端"""
    def _create(response: str):
        client = AsyncMock()
        client.invoke = AsyncMock(return_value=response)
        client.ainvoke = AsyncMock(return_value=response)
        return client
    return _create


@pytest.fixture
def mock_llm_json_response():
    """创建 JSON 响应的 Mock LLM 客户端"""
    def _create(json_str: str):
        client = AsyncMock()
        client.invoke = AsyncMock(return_value=json_str)
        client.ainvoke = AsyncMock(return_value=json_str)
        return client
    return _create


@pytest.fixture
def sample_agent_state():
    """示例 Agent 状态"""
    return {
        "messages": [],
        "user_input": "什么是退货政策？",
        "conversation_id": "test-conv-id",
        "user_id": "test-user-id",
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
    }


@pytest.fixture
def mock_rag_results():
    """Mock RAG 检索结果"""
    return [
        {"content": "退货政策：30天内可申请退货，需保持商品完整", "score": 0.95, "source": "knowledge_base"},
        {"content": "退货流程：1. 登录账户 2. 申请退货 3. 寄回商品", "score": 0.88, "source": "knowledge_base"},
    ]
