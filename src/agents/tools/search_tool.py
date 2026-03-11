"""
搜索工具
Agent 可调用的知识库搜索工具
"""

from typing import Optional

from langchain_core.tools import tool

from src.core.logging import get_logger

logger = get_logger(__name__)


@tool
async def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """
    搜索知识库获取相关信息。

    Args:
        query: 搜索查询文本
        top_k: 返回的最大结果数

    Returns:
        搜索结果的文本摘要
    """
    try:
        from src.rag.retriever import HybridRetriever
        retriever = HybridRetriever()
        results = await retriever.retrieve(query, top_k=top_k)
        if results:
            return "\n\n".join(
                f"[{i+1}] {doc['content']}"
                for i, doc in enumerate(results)
            )
        return "未找到相关信息。"
    except Exception as e:
        logger.error("知识库搜索工具调用失败: %s", e)
        return f"搜索失败: {e}"
