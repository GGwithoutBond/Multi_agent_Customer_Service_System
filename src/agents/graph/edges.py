"""
LangGraph 条件边逻辑
定义图中的路由分支条件
支持多 Worker 并行路由
"""

from typing import Any
from langgraph.graph import END

from src.core.logging import get_logger

logger = get_logger(__name__)


def route_to_worker(state: dict[str, Any]) -> str:
    """
    根据 Orchestrator 的路由决策，选择对应的 Worker 节点

    Returns:
        目标 Worker 节点名称
    """
    worker_type = state.get("worker_type", "faq_worker")

    valid_workers = {
        "faq_worker",
        "order_worker",
        "product_worker",
        "complaint_worker",
        "human_worker",
    }

    if worker_type not in valid_workers:
        logger.warning("未知的 Worker 类型: %s，降级到 faq_worker", worker_type)
        worker_type = "faq_worker"

    logger.info("路由决策: → %s", worker_type)
    return worker_type


def route_after_worker(state: dict[str, Any]) -> str:
    """Worker 执行完毕后，进入质量审查"""
    # 强制进入质量审查
    return "quality_review"

def route_after_review(state: dict[str, Any]) -> str:
    """质量审查后，判断是否重试或继续"""
    score = state.get("quality_score", 5)
    retry_count = state.get("retry_count", 0)
    
    # 如果分数低且有重试机会，跳回 orchestrator
    if score < 3 and retry_count <= 1:
        logger.warning("触发重试机制: score=%s, retry_count=%s", score, retry_count)
        return "orchestrator"

    # 情绪拦截：高风险情绪 或 (高紧急度 + 投诉)
    urgency = state.get("urgency", "medium")
    intent = state.get("intent", "")
    sentiment = state.get("sentiment", "neutral")
    
    if (urgency == "critical" and intent == "complaint") or sentiment in ("angry", "frustrated"):
        logger.info("⚠️ 紧急情况或情绪高危 (%s)，直接返回不再调用额外节点", sentiment)
        # FIXME: 纯状态修改不该放在边函数，但这保留原有的快速处理逻辑
        return END

    if state.get("web_search", False):
        return "web_search"
    return END


def should_continue(state: dict[str, Any]) -> str:
    """
    判断是否需要继续处理或结束

    Returns:
        "continue" 或 "end"
    """
    if state.get("error"):
        return "end"
    if state.get("needs_human"):
        return "end"
    if state.get("response"):
        return "end"
    return "continue"
