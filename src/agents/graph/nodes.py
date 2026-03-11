"""
LangGraph 图节点函数
每个节点对应一个处理步骤
"""

from typing import Any

from src.agents.orchestrator.agent import OrchestratorAgent
from src.agents.workers.complaint_worker import ComplaintWorker
from src.agents.workers.faq_worker import FAQWorker
from src.agents.workers.human_worker import HumanWorker
from src.agents.workers.order_worker import OrderWorker
from src.agents.workers.product_worker import ProductWorker
from src.agents.tools.web_search_tool import web_search
from src.core.logging import get_logger
from src.llm import get_llm_client
from langchain_core.messages import HumanMessage
from src.llm.prompt_templates import QUALITY_REVIEW_PROMPT
import json

logger = get_logger(__name__)

# 单例实例
_orchestrator = OrchestratorAgent()
_faq_worker = FAQWorker()
_order_worker = OrderWorker()
_product_worker = ProductWorker()
_complaint_worker = ComplaintWorker()
_human_worker = HumanWorker()


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
    """质量审查节点 - 评估 Worker 回答质量，低分自动打回重试"""
    worker_result = state.get("worker_result", "")
    user_input = state.get("user_input", "")
    retry_count = state.get("retry_count", 0)
    
    # 如果 Worker 没有生成结果，或者已经重试过，直接跳过审查
    if not worker_result or retry_count >= 1:
        return {"quality_score": 5, "retry_count": retry_count}
        
    try:
        llm_client = get_llm_client()
        prompt = QUALITY_REVIEW_PROMPT.format(
            user_message=user_input,
            worker_result=worker_result
        )
        
        # 尝试使用 JSON 模式
        try:
            result_text = await llm_client.invoke(
                [HumanMessage(content=prompt)],
                response_format={"type": "json_object"}
            )
        except Exception:
            # 降级不使用 json_object
            result_text = await llm_client.invoke([HumanMessage(content=prompt)])
            
        # 简单解析 JSON
        score = 5
        try:
            # 去除可能的 markdown 标记
            text = result_text.strip()
            if "```" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end > start:
                    text = text[start:end]
            result = json.loads(text)
            score = int(result.get("score", 5))
            reason = result.get("reason", "")
            logger.info("质量审查得分: %d, 理由: %s", score, reason)
        except Exception as e:
            logger.warning("解析质量审查结果失败: %s", e)
            
        if score < 3:
            logger.warning("质量审查未通过 (得分 %d)，准备重试！", score)
            return {"quality_score": score, "retry_count": retry_count + 1, "quality_reason": reason}
            
        return {"quality_score": score}
        
    except Exception as e:
        logger.error("质量审查节点异常: %s", e)
        return {"quality_score": 5}
