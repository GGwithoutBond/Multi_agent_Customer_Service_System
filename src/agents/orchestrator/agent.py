"""
Orchestrator Agent (编排器)
负责意图识别、任务分解、路由决策和结果聚合
支持单 Worker 跳过聚合、情感检测、工作记忆
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.base import BaseAgent
from src.agents.orchestrator.router import route_decision
from src.agents.orchestrator.state import AgentState
from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import ORCHESTRATOR_AGGREGATE_PROMPT

logger = get_logger(__name__)


class OrchestratorAgent(BaseAgent):
    """编排器 Agent"""

    def __init__(self):
        super().__init__(
            name="orchestrator",
            description="负责意图识别、任务路由和结果聚合的编排器",
        )

    async def process(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        编排器处理逻辑:
        1. 分析用户意图（含情感/紧急度检测）
        2. 确定路由目标
        3. 存储工作记忆
        """
        user_input = state.get("user_input", "")
        logger.info("Orchestrator 开始处理: %s", user_input[:100])

        # 执行路由决策（单次 LLM 调用，含情感分析）
        decision = await route_decision(user_input)

        sentiment = decision.get("sentiment", "neutral")
        urgency = decision.get("urgency", "medium")

        # 记录情感状态
        if sentiment in ("negative", "angry"):
            logger.warning(
                "⚠️ 用户情感: %s, 紧急度: %s, 输入: %s",
                sentiment, urgency, user_input[:80],
            )

        # 构建工作记忆快照
        working_memory = {
            "intent": decision.get("intent", "unknown"),
            "sentiment": sentiment,
            "urgency": urgency,
            "sub_tasks": decision.get("sub_tasks", []),
            "reasoning": decision.get("reasoning", ""),
        }

        return {
            "intent": decision.get("intent", "unknown"),
            "worker_type": decision.get("worker_type", "faq_worker"),
            "sentiment": sentiment,
            "urgency": urgency,
            "working_memory": working_memory,
            "context": {
                **state.get("context", {}),
                "sub_tasks": decision.get("sub_tasks", []),
                "reasoning": decision.get("reasoning", ""),
                "sentiment": sentiment,
                "urgency": urgency,
            },
        }

    async def aggregate_response(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        聚合 Worker 的处理结果，生成最终响应。

        优化：
        - 无联网搜索时直接返回 Worker 结果（跳过二次 LLM 调用）
        - 有联网搜索时调用 LLM 融合结果
        """
        user_input = state.get("user_input", "")
        worker_type = state.get("worker_type", "unknown")
        worker_result = state.get("worker_result", "")
        web_search_result = state.get("web_search_result", "")

        if not worker_result and not web_search_result:
            return {
                "response": "抱歉，我暂时无法处理您的请求。请稍后再试或联系人工客服。",
                "messages": [AIMessage(content="抱歉，我暂时无法处理您的请求。")],
            }

        # ── 优化 1.5: 无联网搜索时跳过聚合，直接返回 Worker 结果 ──
        if not web_search_result and worker_result:
            logger.info("单 Worker 无联网搜索，跳过聚合直接返回")
            return {
                "response": worker_result,
                "messages": [AIMessage(content=worker_result)],
            }

        # ── 有联网搜索时，调用 LLM 聚合 ──
        try:
            llm_client = get_llm_client()

            # Fix 8: 从 context 获取 persona 风格，传入聚合 prompt
            from src.llm.prompt_templates import DEFAULT_PERSONA, PERSONA_TEMPLATES
            persona_style = state.get("context", {}).get("persona_style")
            persona = PERSONA_TEMPLATES.get(persona_style, DEFAULT_PERSONA) if persona_style else DEFAULT_PERSONA

            base_prompt = ORCHESTRATOR_AGGREGATE_PROMPT.format(
                persona=persona,
                user_message=user_input,
                worker_type=worker_type,
                worker_result=worker_result,
            )

            if web_search_result:
                base_prompt += (
                    f"\n\n## 联网搜索结果（最新互联网信息）\n{web_search_result}\n\n"
                    "请结合以上搜索结果和知识库信息，为用户提供全面且准确的回答。"
                    "如果引用了搜索结果，请标注来源。"
                )

            response = await llm_client.invoke([HumanMessage(content=base_prompt)])

            return {
                "response": response,
                "messages": [AIMessage(content=response)],
            }
        except Exception as e:
            logger.error("Orchestrator 聚合响应失败: %s", e)
            fallback = worker_result or web_search_result
            return {
                "response": fallback,
                "messages": [AIMessage(content=fallback)],
            }
