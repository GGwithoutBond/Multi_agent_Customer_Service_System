"""
MCP 客户端封装
管理与淘宝 MCP Server 的连接，提供工具加载和数据同步的上下文管理器
"""

import traceback
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from langchain_core.messages import ToolMessage
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from src.core.logging import get_logger

logger = get_logger(__name__)

# 默认的淘宝 MCP Server 地址
TAOBAO_MCP_URL = "http://localhost:3654/mcp"


@asynccontextmanager
async def taobao_mcp_session(
    mcp_url: str = TAOBAO_MCP_URL,
) -> AsyncGenerator[tuple[ClientSession | None, list], None]:
    """
    淘宝 MCP 会话上下文管理器。
    """
    session = None
    try:
        logger.info("正在创建 MCP 连接: %s", mcp_url)
        # streamable_http_client 返回 3 个值: (read_stream, write_stream, get_session_id)
        async with streamable_http_client(mcp_url) as (read_stream, write_stream, get_session_id):
            logger.info("MCP transport 创建成功")

            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()
            logger.info("MCP Session 初始化成功")

            # 加载 MCP 工具
            from langchain_mcp_adapters.tools import load_mcp_tools
            mcp_tools = await load_mcp_tools(session, tool_name_prefix=False)
            logger.info("MCP 工具加载成功: %s", [t.name for t in mcp_tools])

            yield session, mcp_tools

    except Exception as e:
        logger.error("MCP 会话异常: %s\n%s", e, traceback.format_exc())
        yield None, []
    finally:
        if session:
            try:
                await session.__aexit__(None, None, None)
            except Exception as close_err:
                logger.warning("关闭 session 时出错: %s", close_err)


def extract_tool_results(messages: list) -> dict[str, Any]:
    """从消息列表中提取工具调用结果"""
    results: dict[str, Any] = {}

    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", None)
            if tool_name:
                content = msg.content
                if isinstance(content, str):
                    try:
                        import json
                        content = json.loads(content)
                    except (json.JSONDecodeError, ValueError):
                        pass
                results[tool_name] = content

    return results
