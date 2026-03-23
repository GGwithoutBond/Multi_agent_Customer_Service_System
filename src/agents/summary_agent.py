"""
Summary Agent
负责会话摘要生成、关键信息提取与标题建议
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from src.agents.base import BaseAgent
from src.agents.json_utils import extract_json_dict
from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import SUMMARY_AGENT_PROMPT

logger = get_logger(__name__)


class SummaryAgent(BaseAgent):
    """摘要与会话命名 Agent"""

    def __init__(self):
        super().__init__(
            name="summary_agent",
            description="生成会话摘要、关键点和会话标题",
        )

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        user_message = str(state.get("user_message", "") or "").strip()
        assistant_message = str(state.get("assistant_message", "") or "").strip()

        if not user_message and not assistant_message:
            return {
                "title": "新对话",
                "summary": "",
                "key_points": [],
            }

        try:
            llm_client = get_llm_client()
            prompt = SUMMARY_AGENT_PROMPT.format(
                user_message=user_message,
                assistant_message=assistant_message,
            )

            try:
                result_text = await llm_client.invoke(
                    [HumanMessage(content=prompt)],
                    response_format={"type": "json_object"},
                )
            except Exception:
                result_text = await llm_client.invoke([HumanMessage(content=prompt)])

            payload = extract_json_dict(result_text) or {}

            title = self._normalize_title(
                payload.get("title"),
                user_message=user_message,
                assistant_message=assistant_message,
            )
            summary = self._normalize_summary(
                payload.get("summary"),
                user_message=user_message,
                assistant_message=assistant_message,
            )
            key_points = self._normalize_key_points(payload.get("key_points"))

            if not key_points:
                key_points = self._fallback_key_points(user_message, assistant_message)

            return {
                "title": title,
                "summary": summary,
                "key_points": key_points,
            }
        except Exception as e:
            logger.warning("SummaryAgent 执行失败，使用降级策略: %s", e)
            return {
                "title": self._normalize_title(
                    None,
                    user_message=user_message,
                    assistant_message=assistant_message,
                ),
                "summary": self._normalize_summary(
                    None,
                    user_message=user_message,
                    assistant_message=assistant_message,
                ),
                "key_points": self._fallback_key_points(user_message, assistant_message),
            }

    @staticmethod
    def _normalize_title(
        raw_title: Any,
        *,
        user_message: str,
        assistant_message: str,
        max_len: int = 30,
    ) -> str:
        text = str(raw_title or "").strip().replace("\n", " ")
        if not text:
            base = user_message or assistant_message or "新对话"
            base = base.replace("\n", " ").strip()
            text = base or "新对话"
        if len(text) > max_len:
            return text[:max_len].rstrip() + "..."
        return text

    @staticmethod
    def _normalize_summary(
        raw_summary: Any,
        *,
        user_message: str,
        assistant_message: str,
        max_len: int = 1000,
    ) -> str:
        text = str(raw_summary or "").strip()
        if not text:
            text = (
                f"用户诉求：{user_message or '未提供'}\n"
                f"客服回复：{assistant_message or '未提供'}"
            )
        if len(text) > max_len:
            return text[:max_len].rstrip()
        return text

    @staticmethod
    def _normalize_key_points(raw_key_points: Any) -> list[str]:
        if not isinstance(raw_key_points, list):
            return []
        points: list[str] = []
        for item in raw_key_points:
            text = str(item).strip()
            if text and text not in points:
                points.append(text)
        return points[:5]

    @staticmethod
    def _fallback_key_points(user_message: str, assistant_message: str) -> list[str]:
        points: list[str] = []
        if user_message:
            points.append(f"用户问题：{user_message[:80]}")
        if assistant_message:
            points.append(f"回复结论：{assistant_message[:80]}")
        return points[:5]
