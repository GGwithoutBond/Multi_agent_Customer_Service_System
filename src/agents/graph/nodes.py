"""
LangGraph 图节点函数
每个节点对应一个处理步骤
"""

from typing import Any

from src.agents.quality_agent import QualityAgent
from src.agents.orchestrator.agent import OrchestratorAgent
from src.agents.workers.complaint_worker import ComplaintWorker
from src.agents.workers.faq_worker import FAQWorker
from src.agents.workers.human_worker import HumanWorker
from src.agents.workers.order_worker import OrderWorker
from src.agents.workers.product_worker import ProductWorker
from src.agents.tools.web_search_tool import web_search
from src.core.logging import get_logger

logger = get_logger(__name__)

# 单例实例
_orchestrator = OrchestratorAgent()
_faq_worker = FAQWorker()
_order_worker = OrderWorker()
_product_worker = ProductWorker()
_complaint_worker = ComplaintWorker()
_human_worker = HumanWorker()
_quality_agent = QualityAgent()


async def orchestrator_node(state: dict[str, Any]) -> dict[str, Any]:
    """编排器节点 - 分析意图并路由"""
    return await _orchestrator.process(state)


async def web_search_node(state: dict[str, Any]) -> dict[str, Any]:
    """联网搜索节点 - 从互联网检索实时信息"""
    user_input = state.get("user_input", "")
    logger.info("联网搜索: %s", user_input[:100])
    result = await web_search(user_input, max_results=5)
    return {"web_search_result": result}


async def faq_worker_node(state: dict[str, Any]) -> dict[str, Any]:
    """FAQ Worker 节点"""
    return await _faq_worker.process(state)


async def order_worker_node(state: dict[str, Any]) -> dict[str, Any]:
    """订单 Worker 节点"""
    return await _order_worker.process(state)


async def product_worker_node(state: dict[str, Any]) -> dict[str, Any]:
    """产品 Worker 节点"""
    return await _product_worker.process(state)


async def complaint_worker_node(state: dict[str, Any]) -> dict[str, Any]:
    """投诉 Worker 节点"""
    return await _complaint_worker.process(state)


async def human_worker_node(state: dict[str, Any]) -> dict[str, Any]:
    """转人工 Worker 节点"""
    result = await _human_worker.process(state)
    result["needs_human"] = True
    return result


async def response_generator_node(state: dict[str, Any]) -> dict[str, Any]:
    """响应生成节点 - 聚合 Worker 结果生成最终回复"""
    return await _orchestrator.aggregate_response(state)

async def quality_review_node(state: dict[str, Any]) -> dict[str, Any]:
    """质量审查节点 - 由 QualityAgent 统一处理评分与风险检测。"""
    return await _quality_agent.process(state)
