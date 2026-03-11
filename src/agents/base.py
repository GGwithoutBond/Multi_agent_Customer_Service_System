"""
Agent 基类
定义所有 Agent 的公共接口
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Agent 抽象基类"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description

    @abstractmethod
    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        处理状态并返回更新后的状态

        Args:
            state: 当前的 AgentState 字典

        Returns:
            更新后的状态字典
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"
