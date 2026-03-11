"""
工作记忆 (内存)
管理当前请求的上下文信息，生命周期为单次请求
"""

from typing import Any, Optional


class WorkingMemory:
    """工作记忆 - 存储当前任务的临时上下文"""

    def __init__(self):
        self._context: dict[str, Any] = {}
        self._entities: dict[str, Any] = {}
        self._intent: Optional[str] = None
        self._worker_type: Optional[str] = None
        self._sub_tasks: list[str] = []

    @property
    def intent(self) -> Optional[str]:
        return self._intent

    @intent.setter
    def intent(self, value: str) -> None:
        self._intent = value

    @property
    def worker_type(self) -> Optional[str]:
        return self._worker_type

    @worker_type.setter
    def worker_type(self, value: str) -> None:
        self._worker_type = value

    def set_context(self, key: str, value: Any) -> None:
        """设置上下文变量"""
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文变量"""
        return self._context.get(key, default)

    def add_entity(self, entity_type: str, value: Any) -> None:
        """添加提取到的实体"""
        self._entities[entity_type] = value

    def get_entities(self) -> dict[str, Any]:
        """获取所有实体"""
        return self._entities.copy()

    def set_sub_tasks(self, tasks: list[str]) -> None:
        """设置子任务列表"""
        self._sub_tasks = tasks

    def get_sub_tasks(self) -> list[str]:
        return self._sub_tasks.copy()

    def to_dict(self) -> dict[str, Any]:
        """导出为字典"""
        return {
            "intent": self._intent,
            "worker_type": self._worker_type,
            "context": self._context,
            "entities": self._entities,
            "sub_tasks": self._sub_tasks,
        }

    def reset(self) -> None:
        """重置工作记忆"""
        self._context.clear()
        self._entities.clear()
        self._intent = None
        self._worker_type = None
        self._sub_tasks.clear()
