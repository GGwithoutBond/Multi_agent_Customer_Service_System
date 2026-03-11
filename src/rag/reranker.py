"""
重排序模块
对检索结果进行精排
支持 LLM 重排序和关键词打分双模式
"""

from typing import Any

from langchain_core.messages import HumanMessage

from src.core.logging import get_logger
from src.llm import get_llm_client

logger = get_logger(__name__)


class Reranker:
    """
    重排序器
    优先使用 LLM 精排，支持降级到关键词打分
    """

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        对文档进行重排序

        Args:
            query: 原始查询
            documents: 文档内容字符串列表
            top_k: 返回前 K 个

        Returns:
            包含 index 和 score 的排序列表
        """
        if len(documents) <= 1:
            return [{"index": i, "score": 1.0} for i in range(len(documents))]

        try:
            return await self._llm_rerank(query, documents, top_k)
        except Exception as e:
            logger.warning("LLM 重排序失败: %s, 降级到关键词打分", e)
            return self._keyword_rerank(query, documents, top_k)

    async def _llm_rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """使用 LLM 进行文档重排序"""
        llm_client = get_llm_client()

        docs_text = "\n\n".join(
            f"[文档{i+1}]: {doc[:300]}"
            for i, doc in enumerate(documents)
        )

        prompt = (
            f"请根据查询与文档的相关性，对以下文档进行评分（0-10分）。\n\n"
            f"查询: {query}\n\n"
            f"{docs_text}\n\n"
            f"请为每个文档打分，格式为: 文档编号:分数，每行一个。只输出打分结果。"
        )

        result = await llm_client.invoke([HumanMessage(content=prompt)])

        # 解析评分
        scores = self._parse_scores(result, len(documents))

        # 构建排序结果
        indexed_scores = [
            {"index": i, "score": score}
            for i, score in enumerate(scores)
        ]
        indexed_scores.sort(key=lambda x: x["score"], reverse=True)

        return indexed_scores[:top_k]

    def _keyword_rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """基于关键词重叠度的简单重排序（降级方案）"""
        query_lower = query.lower()
        keywords = [w for w in query_lower.split() if len(w) > 1]

        scored = []
        for i, doc in enumerate(documents):
            doc_lower = doc.lower()
            if keywords:
                match_count = sum(1 for kw in keywords if kw in doc_lower)
                score = match_count / len(keywords)
            else:
                score = 0.5
            scored.append({"index": i, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _parse_scores(result: str, num_docs: int) -> list[float]:
        """解析 LLM 返回的评分"""
        scores = [5.0] * num_docs  # 默认分数
        for line in result.strip().split("\n"):
            try:
                parts = line.strip().split(":")
                if len(parts) >= 2:
                    idx = int("".join(filter(str.isdigit, parts[0]))) - 1
                    score = float(parts[-1].strip())
                    if 0 <= idx < num_docs:
                        scores[idx] = score
            except (ValueError, IndexError):
                continue
        return scores


# 兼容别名
LLMReranker = Reranker
