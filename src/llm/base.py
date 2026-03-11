"""
LLM 基类
定义统一的 LLM 调用接口
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional

from langchain_core.messages import BaseMessage


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    async def invoke(
        self,
        messages: list[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        """同步调用 LLM"""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """流式调用 LLM"""
        ...

    @abstractmethod
    def get_chat_model(self, **kwargs: Any) -> Any:
        """获取 LangChain ChatModel 实例, 用于 LangGraph 集成"""
        ...
