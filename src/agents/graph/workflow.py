"""
LangGraph 工作流定义
构建完整的 Agent 处理流程图
"""

from langgraph.graph import END, StateGraph

from src.agents.graph.edges import route_after_worker, route_after_review, route_to_worker
from src.agents.graph.nodes import (
    complaint_worker_node,
    faq_worker_node,
    human_worker_node,
    orchestrator_node,
    order_worker_node,
    product_worker_node,
    web_search_node,
    quality_review_node,
)
from src.agents.orchestrator.state import AgentState
from src.core.logging import get_logger

logger = get_logger(__name__)


def build_workflow() -> StateGraph:
    """
    构建 LangGraph 工作流

    流程:
    START → orchestrator → (条件路由) → worker → [web_search] → response_generator → END

    优化说明:
    - response_generator 在无联网搜索时跳过 LLM 聚合，直接返回 Worker 结果
    - 支持情感/紧急度传递
    - critical+complaint 自动标记需要转人工
    """
    workflow = StateGraph(AgentState)

    # ── 添加节点 ──
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("faq_worker", faq_worker_node)
    workflow.add_node("order_worker", order_worker_node)
    workflow.add_node("product_worker", product_worker_node)
    workflow.add_node("complaint_worker", complaint_worker_node)
    workflow.add_node("human_worker", human_worker_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("quality_review", quality_review_node)

    # ── 设置入口 ──
    workflow.set_entry_point("orchestrator")

    # ── 条件路由: orchestrator → worker ──
    workflow.add_conditional_edges(
        "orchestrator",
        route_to_worker,
        {
            "faq_worker": "faq_worker",
            "order_worker": "order_worker",
            "product_worker": "product_worker",
            "complaint_worker": "complaint_worker",
            "human_worker": "human_worker",
        },
    )

    # ── Worker → 质量审查 ──
    for worker in ["faq_worker", "order_worker", "product_worker", "complaint_worker", "human_worker"]:
        workflow.add_edge(worker, "quality_review")

    # ── 质量审查 → (重试/继续) ──
    workflow.add_conditional_edges(
        "quality_review",
        route_after_review,
        {
            "orchestrator": "orchestrator",
            "web_search": "web_search",
            END: END,
        },
    )

    # ── 联网搜索 → END ──
    workflow.add_edge("web_search", END)

    return workflow


def compile_workflow():
    """编译工作流为可执行的 Runnable"""
    workflow = build_workflow()
    return workflow.compile()


# 全局编译后的工作流实例
_compiled_workflow = None


def get_workflow():
    """获取编译后的工作流单例"""
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = compile_workflow()
        logger.info("LangGraph 工作流已编译")
    return _compiled_workflow
