"""
联网搜索工具
使用 Tavily Search API 获取实时网络信息
"""

import httpx

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"


async def web_search(query: str, max_results: int = 5) -> str:
    """
    使用 Tavily API 进行联网搜索

    Args:
        query: 搜索查询
        max_results: 最大结果数

    Returns:
        格式化的搜索结果文本
    """
    settings = get_settings()
    api_key = settings.TAVILY_API_KEY

    if not api_key:
        logger.error("TAVILY_API_KEY 未配置")
        return "联网搜索不可用（缺少 TAVILY_API_KEY 配置）。"

    try:
        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
            "include_answer": True,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(TAVILY_API_URL, json=payload)
            response.raise_for_status()
            data = response.json()

        # 提取 Tavily 直接生成的答案摘要
        answer = data.get("answer", "")

        # 提取搜索结果
        results = data.get("results", [])

        if not results and not answer:
            return "未找到相关搜索结果。"

        formatted = []

        if answer:
            formatted.append(f"📋 摘要: {answer}")

        for i, r in enumerate(results, 1):
            title = r.get("title", "无标题")
            content = r.get("content", "")[:300]
            url = r.get("url", "")
            formatted.append(f"[{i}] {title}\n{content}\n来源: {url}")

        logger.info("Tavily 搜索完成，返回 %d 条结果", len(results))
        return "\n\n".join(formatted)

    except httpx.TimeoutException:
        logger.error("Tavily 搜索超时: %s", query)
        return "联网搜索超时，请稍后重试。"
    except httpx.HTTPStatusError as e:
        logger.error("Tavily API 错误: %s %s", e.response.status_code, e.response.text)
        return f"联网搜索 API 错误: {e.response.status_code}"
    except Exception as e:
        logger.error("联网搜索失败: %s", e)
        return f"联网搜索出错: {e}"
