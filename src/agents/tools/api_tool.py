"""
外部 API 调用工具
Agent 可调用的外部服务接口
"""

import httpx
from langchain_core.tools import tool

from src.core.logging import get_logger

logger = get_logger(__name__)


@tool
async def call_external_api(url: str, method: str = "GET", payload: str = "") -> str:
    """
    调用外部 API 获取数据。

    Args:
        url: API 地址
        method: HTTP 方法 (GET/POST)
        payload: 请求体 (JSON 字符串)

    Returns:
        API 响应文本
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if method.upper() == "POST":
                response = await client.post(url, content=payload)
            else:
                response = await client.get(url)

            response.raise_for_status()
            return response.text[:2000]  # 限制返回长度
    except Exception as e:
        logger.error("外部 API 调用失败: %s - %s", url, e)
        return f"API 调用失败: {e}"
