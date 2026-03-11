"""
Orchestrator 路由决策
根据意图将任务路由到合适的 Worker
支持结构化 JSON 输出，单次 LLM 调用完成意图+情感+路由
"""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import (
    INTENT_CLASSIFICATION_PROMPT,
    ORCHESTRATOR_SYSTEM_PROMPT,
    SENTIMENT_ANALYSIS_PROMPT,
)

logger = get_logger(__name__)

# 意图到 Worker 的映射
INTENT_WORKER_MAP: dict[str, str] = {
    "faq": "faq_worker",
    "order": "order_worker",
    "product": "product_worker",
    "complaint": "complaint_worker",
    "human": "human_worker",
    "greeting": "faq_worker",
    "unknown": "faq_worker",
}

# 有效的 sentiment 和 urgency 值
VALID_SENTIMENTS = {"positive", "neutral", "negative", "angry", "frustrated"}
VALID_URGENCIES = {"low", "medium", "high", "critical"}


def _extract_json_from_response(text: str) -> dict | None:
    """从 LLM 响应中提取 JSON（处理 markdown 代码块等情况）"""
    text = text.strip()
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试从 ```json ... ``` 中提取
    if "```" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return None


async def route_decision(user_message: str) -> dict[str, Any]:
    """
    完整的路由决策（单次 LLM 调用）

    返回包含 intent, worker_type, sentiment, urgency 的决策字典。
    使用结构化 JSON 提示确保一次性返回所有信息。
    """
    try:
        llm_client = get_llm_client()
        messages = [
            SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ]

        # 尝试使用 JSON mode（如果 LLM 支持）
        try:
            result = await llm_client.invoke(
                messages,
                response_format={"type": "json_object"},
            )
        except (TypeError, Exception):
            # 不支持 response_format 参数时回退
            result = await llm_client.invoke(messages)

        # 解析 JSON
        decision = _extract_json_from_response(result)

        if decision:
            # 校验并规范化 worker_type
            worker_type = decision.get("worker_type", "faq")
            if worker_type not in INTENT_WORKER_MAP:
                worker_type = "faq"
            decision["worker_type"] = INTENT_WORKER_MAP.get(worker_type, "faq_worker")

            # 校验 sentiment / urgency
            sentiment = decision.get("sentiment", "neutral")
            if sentiment not in VALID_SENTIMENTS:
                sentiment = "neutral"
            decision["sentiment"] = sentiment

            urgency = decision.get("urgency", "medium")
            if urgency not in VALID_URGENCIES:
                urgency = "medium"
            decision["urgency"] = urgency

            # 自动升级规则：angry + complaint → urgency 至少 high
            if sentiment == "angry" and decision.get("intent") == "complaint":
                if urgency in ("low", "medium"):
                    decision["urgency"] = "high"
                    logger.info("⚠️ 用户愤怒且投诉，自动升级紧急度为 high")

            # 情绪升级规则：多维度综合判断，避免过度拦截
            intent = decision.get("intent", "")
            should_escalate = (
                # 场景1: 极度愤怒 + 高紧急度（必须转人工）
                (sentiment == "angry" and urgency in ("high", "critical"))
                # 场景2: 极度沮丧 + critical 级别（防止用户失控）
                or (sentiment == "frustrated" and urgency == "critical")
                # 场景3: 愤怒 + 投诉意图 + 非低紧急度（投诉链路无法自动解决）
                or (sentiment == "angry" and intent == "complaint" and urgency not in ("low",))
            )

            if should_escalate:
                logger.warning(
                    "🚨 情绪升级至人工 | sentiment=%s urgency=%s intent=%s",
                    sentiment, urgency, intent,
                )
                decision["worker_type"] = "human_worker"
                decision["intent"] = "human"
                decision["urgency"] = "critical"
            elif sentiment in ("angry", "frustrated"):
                # 未达升级阈值：路由至 complaint_worker 处理（而非直接转人工）
                if decision.get("worker_type") not in ("complaint_worker", "human_worker"):
                    decision["worker_type"] = "complaint_worker"
                    decision["intent"] = "complaint"
                logger.info(
                    "⚠️ 用户情绪不佳 (%s)，路由至 complaint_worker（未达升级阈值）",
                    sentiment,
                )

            return decision

        # ─── JSON 解析失败，降级为简单意图分类 ───
        logger.warning("Orchestrator JSON 解析失败，降级到简单分类")
        intent = await classify_intent(user_message)
        return {
            "intent": intent,
            "worker_type": INTENT_WORKER_MAP.get(intent, "faq_worker"),
            "sentiment": "neutral",
            "urgency": "medium",
            "sub_tasks": [],
            "reasoning": "降级到简单意图分类",
        }

    except Exception as e:
        logger.error("路由决策失败: %s", e)
        return {
            "intent": "unknown",
            "worker_type": "faq_worker",
            "sentiment": "neutral",
            "urgency": "medium",
            "sub_tasks": [],
            "reasoning": f"路由决策异常: {e}",
        }


async def classify_intent(user_message: str) -> str:
    """
    降级用：简单意图分类（单次 LLM 调用）
    """
    try:
        llm_client = get_llm_client()
        prompt = INTENT_CLASSIFICATION_PROMPT.format(user_message=user_message)
        result = await llm_client.invoke([HumanMessage(content=prompt)])
        intent = result.strip().lower()

        valid_intents = {"faq", "order", "product", "complaint", "human", "greeting", "unknown"}
        if intent not in valid_intents:
            logger.warning("LLM 返回了未知意图: %s, 降级为 unknown", intent)
            intent = "unknown"

        return intent
    except Exception as e:
        logger.error("意图分类失败: %s", e)
        return "unknown"


def get_worker_type(intent: str) -> str:
    """根据意图获取 Worker 类型"""
    return INTENT_WORKER_MAP.get(intent, "faq_worker")
