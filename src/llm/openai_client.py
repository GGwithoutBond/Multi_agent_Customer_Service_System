"""
OpenAI / GPT-4 客户端
"""

from typing import Any, AsyncIterator, Optional

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from src.core.config import get_settings
from src.core.logging import get_logger
from src.llm.base import BaseLLMClient

logger = get_logger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI LLM 客户端"""

    def __init__(self):
        settings = get_settings()
        self._default_model = settings.OPENAI_MODEL
        self._api_key = settings.OPENAI_API_KEY
        self._api_base = settings.OPENAI_API_BASE
        self._temperature = settings.LLM_TEMPERATURE
        self._max_tokens = settings.LLM_MAX_TOKENS

    def get_chat_model(self, **kwargs: Any) -> ChatOpenAI:
        """获取 ChatOpenAI 实例"""
        params: dict[str, Any] = {
            "model": kwargs.pop("model", self._default_model),
            "temperature": kwargs.pop("temperature", self._temperature),
            "max_tokens": kwargs.pop("max_tokens", self._max_tokens),
            "api_key": self._api_key,
        }
        if self._api_base:
            params["base_url"] = self._api_base
        params.update(kwargs)
        return ChatOpenAI(**params)

    async def invoke(
        self,
        messages: list[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """调用 OpenAI 获取完整响应"""
        llm = self.get_chat_model(
            temperature=temperature or self._temperature,
            max_tokens=max_tokens or self._max_tokens,
            **kwargs,
        )
        response = await llm.ainvoke(messages)
        return str(response.content)

    async def stream(
        self,
        messages: list[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式调用 OpenAI"""
        llm = self.get_chat_model(
            temperature=temperature or self._temperature,
            max_tokens=max_tokens or self._max_tokens,
            streaming=True,
            **kwargs,
        )
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield str(chunk.content)
