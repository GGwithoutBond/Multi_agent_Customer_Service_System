"""
记忆基类
定义记忆系统的统一接口
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseMemory(ABC):
    """记忆抽象基类"""

    @abstractmethod
    async def load(self, session_id: str) -> list[dict[str, Any]]:
        """加载记忆"""
        ...

    @abstractmethod
    async def save(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """保存记忆"""
        ...

    @abstractmethod
    async def clear(self, session_id: str) -> None:
        """清除记忆"""
        ...
