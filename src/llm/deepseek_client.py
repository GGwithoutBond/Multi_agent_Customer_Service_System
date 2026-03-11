"""
DeepSeek 客户端（兼容 OpenAI API）
"""

from typing import Any
from langchain_openai import ChatOpenAI
from src.core.config import get_settings
from src.llm.base import BaseLLMClient

class DeepSeekClient(BaseLLMClient):
    """DeepSeek LLM 客户端"""

    def __init__(self):
        settings = get_settings()
        self._default_model = settings.DEEPSEEK_MODEL
        self._api_key = settings.DEEPSEEK_API_KEY
        self._api_base = settings.DEEPSEEK_API_BASE
        self._temperature = settings.LLM_TEMPERATURE
        self._max_tokens = settings.LLM_MAX_TOKENS

    def get_chat_model(self, **kwargs: Any) -> ChatOpenAI:
        params = {
            "model": kwargs.pop("model", self._default_model),
            "temperature": kwargs.pop("temperature", self._temperature),
            "max_tokens": kwargs.pop("max_tokens", self._max_tokens),
            "api_key": self._api_key,
        }
        if self._api_base:
            params["base_url"] = self._api_base
        params.update(kwargs)
        return ChatOpenAI(**params)

    async def invoke(self, *args, **kwargs) -> str:
        # 复用 OpenAIClient 的 invoke 逻辑
        from src.llm.openai_client import OpenAIClient
        return await OpenAIClient.invoke(self, *args, **kwargs)

    async def stream(self, *args, **kwargs):
        # 复用 OpenAIClient 的 stream 逻辑
        from src.llm.openai_client import OpenAIClient
        async for chunk in OpenAIClient.stream(self, *args, **kwargs):
            yield chunk