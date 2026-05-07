"""FAQ worker backed by optional knowledge retrieval."""

from typing import Any

from langchain_core.messages import HumanMessage

from src.agents.workers.base_worker import BaseWorker
from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import FAQ_WORKER_PROMPT

logger = get_logger(__name__)


class FAQWorker(BaseWorker):
    """Handle FAQ-style requests with optional retrieval support."""

    def __init__(self):
        super().__init__(
            name="faq_worker",
            description="Handle FAQ-style requests with knowledge retrieval support.",
        )

    async def handle(self, user_input: str, context: dict[str, Any], history: str = "") -> str:
        """Generate a response from the worker prompt and retrieval context."""
        rag_context = await self._retrieve_knowledge(user_input, context)

        llm_client = get_llm_client()
        prompt = FAQ_WORKER_PROMPT.format(
            persona=self._get_persona(context),
            context=rag_context,
            user_message=user_input,
            history=history,
        )
        response = await llm_client.invoke([HumanMessage(content=prompt)])
        return response

    async def _retrieve_knowledge(self, query: str, context: dict[str, Any]) -> str:
        """Fetch retrieval context unless the caller disables it for evaluation."""
        enable_retrieval = context.get("enable_retrieval", True)
        if not enable_retrieval:
            return "Knowledge retrieval disabled for this run. Answer from general knowledge only."

        use_vector = context.get("use_vector", True)
        use_graph = context.get("use_graph", True)
        use_reranker = context.get("use_reranker", True)

        try:
            from src.rag.retriever import HybridRetriever

            retriever = HybridRetriever()
            results = await retriever.retrieve(
                query,
                top_k=5,
                use_vector=use_vector,
                use_graph=use_graph,
                use_reranker=use_reranker,
            )
            if results:
                return "\n\n".join(f"[{i + 1}] {doc['content']}" for i, doc in enumerate(results))
            return "No matching knowledge-base content was found."
        except Exception as exc:
            logger.warning("Knowledge retrieval failed, falling back to direct LLM answer: %s", exc)
            return "Knowledge retrieval is temporarily unavailable. Answer from general knowledge only."
