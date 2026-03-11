"""
Anthropic Claude 客户端
"""

from typing import Any, AsyncIterator, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage

from src.core.config import get_settings
from src.core.logging import get_logger
from src.llm.base import BaseLLMClient

logger = get_logger(__name__)


class ClaudeClient(BaseLLMClient):
    """Claude LLM 客户端"""

    def __init__(self):
        settings = get_settings()
        self._default_model = settings.ANTHROPIC_MODEL
        self._api_key = settings.ANTHROPIC_API_KEY
        self._temperature = settings.LLM_TEMPERATURE
        self._max_tokens = settings.LLM_MAX_TOKENS

    def get_chat_model(self, **kwargs: Any) -> ChatAnthropic:
        """获取 ChatAnthropic 实例"""
        params: dict[str, Any] = {
            "model": kwargs.pop("model", self._default_model),
            "temperature": kwargs.pop("temperature", self._temperature),
            "max_tokens": kwargs.pop("max_tokens", self._max_tokens),
            "anthropic_api_key": self._api_key,
        }
        params.update(kwargs)
        return ChatAnthropic(**params)

    async def invoke(
        self,
        messages: list[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """调用 Claude 获取完整响应"""
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
        """流式调用 Claude"""
        llm = self.get_chat_model(
            temperature=temperature or self._temperature,
            max_tokens=max_tokens or self._max_tokens,
            streaming=True,
            **kwargs,
        )
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield str(chunk.content)
