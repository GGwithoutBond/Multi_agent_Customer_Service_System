"""
LLM 集成模块
提供统一的 LLM 客户端工厂
"""

import imp
from typing import Optional

from src.core.config import get_settings
from src.llm.base import BaseLLMClient
from src.llm.openai_client import OpenAIClient
from src.llm.claude_client import ClaudeClient
from src.llm.deepseek_client import DeepSeekClient

def get_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """
    获取 LLM 客户端

    Args:
        provider: LLM 提供商 (openai / anthropic)，默认使用配置值
    """
    provider = provider or get_settings().DEFAULT_LLM_PROVIDER

    if provider == "openai":
        return OpenAIClient()
    elif provider == "anthropic":
        return ClaudeClient()
    elif provider == "deepseek":
        return DeepSeekClient()
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")
