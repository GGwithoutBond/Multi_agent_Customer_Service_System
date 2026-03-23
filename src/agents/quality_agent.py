"""
质量审查 Agent
用于评估回复质量并输出风险标记。
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from src.agents.base import BaseAgent
from src.agents.json_utils import extract_json_dict
from src.core.config import get_settings
from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import QUALITY_AGENT_PROMPT

logger = get_logger(__name__)


class QualityAgent(BaseAgent):
    """质量审查代理。"""

    def __init__(self):
        super().__init__(
            name="quality_agent",
            description="评估回复质量并产出风险信号。",
        )

    @staticmethod
    def _is_high_risk(state: dict[str, Any]) -> bool:
        intent = str(state.get("intent") or "").lower()
        sentiment = str(state.get("sentiment") or "").lower()
        urgency = str(state.get("urgency") or "").lower()

        return (
            intent == "complaint"
            or sentiment in {"angry", "frustrated", "negative"}
            or urgency in {"high", "critical"}
        )

    @classmethod
    def should_run_sync_review(cls, state: dict[str, Any]) -> bool:
        settings = get_settings()
        if not settings.ENABLE_SYNC_QUALITY_REVIEW:
            return False
        if not settings.SYNC_QUALITY_REVIEW_RISK_ONLY:
            return True
        has_risk_fields = any(k in state for k in ("intent", "sentiment", "urgency"))
        if not has_risk_fields:
            # Keep backward compatibility for direct unit tests / ad-hoc calls.
            return True
        return cls._is_high_risk(state)

    @classmethod
    def should_run_async_review(cls, state: dict[str, Any]) -> bool:
        settings = get_settings()
        if not settings.ENABLE_ASYNC_QUALITY_REVIEW:
            return False
        return not cls.should_run_sync_review(state)

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """同步链路质量评估；关闭同步审查时直接透传。"""
        worker_result = state.get("worker_result", "")
        user_input = state.get("user_input", "")
        retry_count = state.get("retry_count", 0)

        # Skip sync review for non-risk requests when configured.
        if not self.should_run_sync_review(state):
            return {
                "quality_score": 5,
                "retry_count": retry_count,
                "quality_reason": "已跳过同步质量审查",
                "quality_risk_flags": [],
            }

        # Avoid endless retry loops.
        if not worker_result or retry_count >= 1:
            return {
                "quality_score": 5,
                "retry_count": retry_count,
                "quality_reason": None,
                "quality_risk_flags": [],
            }

        try:
            evaluated = await self.evaluate_once(user_message=user_input, worker_result=worker_result)
            score = int(evaluated.get("quality_score", 5))
            reason = str(evaluated.get("quality_reason") or "")
            risk_flags = evaluated.get("quality_risk_flags", [])

            logger.info(
                "质检结果 score=%d reason=%s risk=%s",
                score,
                reason,
                ",".join(risk_flags) if risk_flags else "-",
            )

            if score < 3:
                logger.warning("质量审查未通过 (score=%d)，触发重试", score)
                return {
                    "quality_score": score,
                    "retry_count": retry_count + 1,
                    "quality_reason": reason or "回复质量不足",
                    "quality_risk_flags": risk_flags,
                }

            return {
                "quality_score": score,
                "quality_reason": reason or None,
                "quality_risk_flags": risk_flags,
            }

        except Exception as e:
            logger.error("质量审查代理执行失败: %s", e)
            return {
                "quality_score": 5,
                "quality_reason": None,
                "quality_risk_flags": [],
            }

    async def evaluate_once(self, user_message: str, worker_result: str) -> dict[str, Any]:
        """单次评估回答质量（不含重试策略）。"""
        llm_client = get_llm_client()
        prompt = QUALITY_AGENT_PROMPT.format(
            user_message=user_message,
            worker_result=worker_result,
        )

        try:
            result_text = await llm_client.invoke(
                [HumanMessage(content=prompt)],
                response_format={"type": "json_object"},
            )
        except Exception:
            result_text = await llm_client.invoke([HumanMessage(content=prompt)])

        payload = extract_json_dict(result_text) or {}

        raw_score = payload.get("score", 5)
        reason = str(payload.get("reason", "")).strip()
        risk_flags_raw = payload.get("risk_flags", [])

        score = self._normalize_score(raw_score)
        risk_flags = self._normalize_risk_flags(risk_flags_raw)
        return {
            "quality_score": score,
            "quality_reason": reason or None,
            "quality_risk_flags": risk_flags,
        }

    @staticmethod
    def _normalize_score(value: Any) -> int:
        try:
            score = int(value)
        except (TypeError, ValueError):
            return 5
        return max(1, min(5, score))

    @staticmethod
    def _normalize_risk_flags(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized[:5]


