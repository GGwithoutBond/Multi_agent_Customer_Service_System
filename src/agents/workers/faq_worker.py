"""
FAQ Worker Agent
处理常见问题查询，结合 GraphRAG 检索知识库
"""

from typing import Any

from langchain_core.messages import HumanMessage

from src.agents.workers.base_worker import BaseWorker
from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import FAQ_WORKER_PROMPT

logger = get_logger(__name__)


class FAQWorker(BaseWorker):
    """FAQ 处理 Worker"""

    def __init__(self):
        super().__init__(
            name="faq_worker",
            description="处理常见问题查询，基于知识库检索回答",
        )

    async def handle(self, user_input: str, context: dict[str, Any], history: str = "") -> str:
        """FAQ 处理逻辑"""
        # 1. 从 RAG 模块检索相关知识
        rag_context = await self._retrieve_knowledge(user_input)

        # 2. 使用 LLM 生成回答（含对话历史）
        llm_client = get_llm_client()
        prompt = FAQ_WORKER_PROMPT.format(
            persona=self._get_persona(context),
            context=rag_context,
            user_message=user_input,
            history=history,
        )
        response = await llm_client.invoke([HumanMessage(content=prompt)])
        return response

    async def _retrieve_knowledge(self, query: str) -> str:
        """从知识库检索相关信息"""
        try:
            from src.rag.retriever import HybridRetriever
            retriever = HybridRetriever()
            results = await retriever.retrieve(query, top_k=5)
            if results:
                return "\n\n".join(
                    f"[{i+1}] {doc['content']}"
                    for i, doc in enumerate(results)
                )
            return "未找到相关知识库内容。"
        except Exception as e:
            logger.warning("知识库检索失败: %s，将使用 LLM 直接回答", e)
            return "知识库暂不可用，请基于通用知识回答。"
