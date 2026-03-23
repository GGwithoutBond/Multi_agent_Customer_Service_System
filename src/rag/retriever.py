"""
混合检索器
结合向量检索和图检索的混合检索策略
优化: 集成 Reranker 精排、动态图检索分数
"""

import time
from collections import deque
from typing import Any, Optional

from src.core.logging import get_logger
from src.rag.embeddings import embed_text

logger = get_logger(__name__)

# ── 检索指标记录（内存环形缓冲区，最近 200 条） ──
_retrieval_logs: deque[dict[str, Any]] = deque(maxlen=200)


def get_retrieval_logs() -> list[dict[str, Any]]:
    """获取最近的检索指标日志，供 Admin API 调用"""
    return list(_retrieval_logs)


class HybridRetriever:
    """
    混合检索器
    支持: 向量检索 + 图检索 + RRF 融合排序 + Reranker 精排
    """

    def __init__(self):
        self._vector_store = None
        self._graph_store = None
        self._reranker = None

    def _get_vector_store(self):
        if self._vector_store is None:
            from src.rag.vector_store import VectorStore
            self._vector_store = VectorStore()
        return self._vector_store

    def _get_graph_store(self):
        if self._graph_store is None:
            from src.rag.graph_store import GraphStore
            self._graph_store = GraphStore()
        return self._graph_store

    def _get_reranker(self):
        if self._reranker is None:
            try:
                from src.rag.reranker import Reranker
                self._reranker = Reranker()
            except Exception as e:
                logger.warning("重排器初始化失败: %s，跳过精排", e)
        return self._reranker

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_vector: bool = True,
        use_graph: bool = True,
        use_reranker: bool = True,
    ) -> list[dict[str, Any]]:
        """
        混合检索

        Args:
            query: 查询文本
            top_k: 返回的最大结果数
            use_vector: 是否使用向量检索
            use_graph: 是否使用图检索
            use_reranker: 是否使用 Reranker 精排

        Returns:
            检索结果列表, 每项包含 content, score, source 等字段
        """
        t0 = time.time()
        results: list[dict[str, Any]] = []
        vector_count = 0
        graph_count = 0

        # 1. 向量检索
        if use_vector:
            vector_results = await self._vector_search(query, top_k)
            vector_count = len(vector_results)
            results.extend(vector_results)

        # 2. 图检索
        if use_graph:
            graph_results = await self._graph_search(query, top_k)
            graph_count = len(graph_results)
            results.extend(graph_results)

        # 3. RRF 融合排序 (如果多路召回)
        if use_vector and use_graph and results:
            results = self._rrf_fusion(results, top_k * 2)  # 多取一些给 reranker

        # 4. Reranker 精排（优化 4.3）
        reranker_used = False
        if use_reranker and results:
            results = await self._rerank(query, results, top_k)
            reranker_used = True

        final_results = results[:top_k]

        # ── 记录检索指标 ──
        latency_ms = int((time.time() - t0) * 1000)
        scores = [r.get("rerank_score") or r.get("rrf_score") or r.get("score", 0) for r in final_results]
        avg_score = round(sum(scores) / len(scores), 4) if scores else 0
        top_score = round(max(scores), 4) if scores else 0

        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "query": query[:120],
            "top_k": top_k,
            "vector_hits": vector_count,
            "graph_hits": graph_count,
            "total_results": len(final_results),
            "reranker_used": reranker_used,
            "avg_score": avg_score,
            "top_score": top_score,
            "latency_ms": latency_ms,
            "sources": [r.get("source", "unknown") for r in final_results],
            "top_contents": [r.get("content", "")[:80] for r in final_results[:3]],
        }
        _retrieval_logs.appendleft(log_entry)

        return final_results

    async def _vector_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """向量相似度检索"""
        try:
            query_embedding = await embed_text(query)
            vector_store = self._get_vector_store()
            results = await vector_store.search(query_embedding, top_k=top_k)
            for r in results:
                r["source"] = "vector"
            return results
        except Exception as e:
            logger.warning("向量检索失败: %s", e)
            return []

    async def _graph_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """图数据库检索（优化 4.2: 动态分数计算）"""
        try:
            graph_store = self._get_graph_store()
            results = await graph_store.search_by_keyword(query, limit=top_k)
            docs = []
            query_lower = query.lower()

            for r in results:
                props = r.get("props", {})
                name = r.get("name", "")
                description = props.get("description", "")

                content_parts = [f"名称: {name}"]
                if description:
                    content_parts.append(f"描述: {description}")

                # ── 优化 4.2: 动态计算分数（基于关键词重叠度）──
                combined_text = f"{name} {description}".lower()
                keywords = [w for w in query_lower.split() if len(w) > 1]
                if keywords:
                    match_count = sum(1 for kw in keywords if kw in combined_text)
                    score = min(0.3 + (match_count / len(keywords)) * 0.7, 1.0)
                else:
                    score = 0.5

                docs.append({
                    "id": name,
                    "content": "\n".join(content_parts),
                    "metadata": {"types": r.get("types", [])},
                    "score": score,
                    "source": "graph",
                })
            return docs
        except Exception as e:
            logger.warning("图检索失败: %s", e)
            return []

    async def _rerank(
        self,
        query: str,
        results: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """使用 Reranker 进行精排（优化 4.3）"""
        reranker = self._get_reranker()
        if not reranker:
            return results[:top_k]

        try:
            documents = [doc.get("content", "") for doc in results]
            reranked = await reranker.rerank(query, documents, top_k=top_k)

            # 将 reranker 分数回写
            reranked_results = []
            for item in reranked:
                idx = item.get("index", 0)
                if idx < len(results):
                    doc = results[idx].copy()
                    doc["rerank_score"] = item.get("score", 0)
                    reranked_results.append(doc)

            return reranked_results
        except Exception as e:
            logger.warning("重排器精排失败: %s，使用 RRF 排序", e)
            return results[:top_k]

    def _rrf_fusion(
        self, results: list[dict[str, Any]], top_k: int, k: int = 60
    ) -> list[dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) 融合排序

        RRF 公式: score = Σ 1/(k + rank_i)
        """
        # 按 source 分组
        source_groups: dict[str, list[dict]] = {}
        for doc in results:
            source = doc.get("source", "unknown")
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(doc)

        # 对每组按 score 排序
        for source in source_groups:
            source_groups[source].sort(key=lambda x: x.get("score", 0), reverse=True)

        # 计算 RRF 分数
        doc_scores: dict[str, float] = {}
        doc_map: dict[str, dict] = {}

        for source, docs in source_groups.items():
            for rank, doc in enumerate(docs):
                doc_id = doc.get("id", str(rank))
                rrf_score = 1.0 / (k + rank + 1)
                doc_scores[doc_id] = doc_scores.get(doc_id, 0) + rrf_score
                doc_map[doc_id] = doc

        # 按 RRF 分数排序
        sorted_ids = sorted(doc_scores, key=doc_scores.get, reverse=True)
        fused = []
        for doc_id in sorted_ids[:top_k]:
            doc = doc_map[doc_id].copy()
            doc["rrf_score"] = doc_scores[doc_id]
            fused.append(doc)

        return fused
