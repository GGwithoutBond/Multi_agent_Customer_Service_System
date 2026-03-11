"""
Worker Agent 基类
所有 Worker 的公共功能
现在传递对话历史和工作记忆给 Worker
"""

from abc import abstractmethod
from typing import Any

from langchain_core.messages import BaseMessage

from src.agents.base import BaseAgent
from src.core.logging import get_logger
from src.llm.prompt_templates import DEFAULT_PERSONA, PERSONA_TEMPLATES

logger = get_logger(__name__)


class BaseWorker(BaseAgent):
    """Worker Agent 基类"""

    def __init__(self, name: str, description: str = ""):
        super().__init__(name=name, description=description)

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """Worker 处理入口 —— 传递完整上下文给 handle()"""
        user_input = state.get("user_input", "")
        context = state.get("context", {})

        # ── 优化 1.3: 从 messages 提取对话历史 ──
        history_text = self._format_history(state.get("messages", []))

        # 注入工作记忆
        working_memory = state.get("working_memory", {})
        if working_memory:
            context = {**context, "working_memory": working_memory}

        # ── Fix 4: 注入质量审查失败原因（重试时提示 Worker 改进） ──
        quality_reason = state.get("quality_reason")
        retry_count = state.get("retry_count", 0)
        if quality_reason and retry_count > 0:
            context = {
                **context,
                "quality_reason": quality_reason,
                "is_retry": True,
            }
            logger.info(
                "Worker [%s] 重试中，审查失败原因: %s", self.name, quality_reason
            )

        logger.info("Worker [%s] 开始处理: %s", self.name, user_input[:100])

        try:
            result = await self.handle(user_input, context, history_text)
            return {"worker_result": result}
        except Exception as e:
            logger.error("Worker [%s] 处理异常: %s", self.name, e)
            return {"worker_result": None, "error": str(e)}

    @abstractmethod
    async def handle(self, user_input: str, context: dict[str, Any], history: str = "") -> str:
        """
        具体的处理逻辑，由子类实现

        Args:
            user_input: 用户输入
            context: 上下文信息（含工作记忆）
            history: 格式化的对话历史文本

        Returns:
            处理结果文本
        """
        ...

    @staticmethod
    def _format_history(messages: Any, max_turns: int = 6) -> str:
        """将 LangChain messages 格式化为文本对话历史"""
        if not messages:
            return "（无历史对话）"

        lines = []
        for msg in messages[-(max_turns * 2):]:
            role = getattr(msg, "type", "unknown")
            content = getattr(msg, "content", "")
            if not content:
                continue
            if role == "human":
                lines.append(f"用户: {content}")
            elif role == "ai":
                lines.append(f"客服: {content}")
            elif role == "system":
                lines.append(f"[系统: {content[:100]}]")

        return "\n".join(lines) if lines else "（无历史对话）"

    def _get_persona(self, context: dict[str, Any]) -> str:
        """从上下文中获取当前指定的 Agent 人设"""
        style = context.get("persona_style")
        return PERSONA_TEMPLATES.get(style, DEFAULT_PERSONA) if style else DEFAULT_PERSONA
