"""Hybrid retrieval utilities for vector and graph search."""

from __future__ import annotations

import re
import time
from collections import deque
from typing import Any

from src.core.logging import get_logger
from src.rag.embeddings import embed_text

logger = get_logger(__name__)

_retrieval_logs: deque[dict[str, Any]] = deque(maxlen=200)

_GRAPH_NOISE_PHRASES = (
    "请问",
    "麻烦问一下",
    "问一下",
    "帮我看看",
    "帮我查一下",
    "给我查一下",
    "给我看看",
    "价格是多少",
    "多少钱",
    "价格",
    "售价",
    "推荐",
    "有哪些",
    "有什么",
    "怎么样",
    "是什么",
    "在哪个平台",
    "哪个平台",
    "是什么芯片",
    "是什么屏幕",
    "屏幕多大",
    "是哪个店铺",
    "哪个店铺",
)
_GRAPH_NOISE_TOKENS = {
    "的",
    "呢",
    "吗",
    "呀",
    "啊",
    "请问",
    "问下",
    "一下",
    "看看",
    "查下",
    "查一下",
    "帮我",
    "告诉我",
    "多少",
}
_GRAPH_PUNCT_RE = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff+\-\.\s]")
_GRAPH_SPACE_RE = re.compile(r"\s+")


def get_retrieval_logs() -> list[dict[str, Any]]:
    """Return recent retrieval log entries."""
    return list(_retrieval_logs)


def clear_retrieval_logs() -> None:
    """Clear recent retrieval log entries for isolated evaluation runs."""
    _retrieval_logs.clear()


class HybridRetriever:
    """Combine vector search and graph search with optional reranking."""

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
            except Exception as exc:
                logger.warning("Failed to initialize reranker, skipping rerank: %s", exc)
        return self._reranker

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_vector: bool = True,
        use_graph: bool = True,
        use_reranker: bool = True,
    ) -> list[dict[str, Any]]:
        """Retrieve documents using vector search, graph search, or both."""
        t0 = time.time()
        results: list[dict[str, Any]] = []
        vector_count = 0
        graph_count = 0

        if use_vector:
            vector_results = await self._vector_search(query, top_k)
            vector_count = len(vector_results)
            results.extend(vector_results)

        if use_graph:
            graph_results = await self._graph_search(query, top_k)
            graph_count = len(graph_results)
            results.extend(graph_results)

        if use_vector and use_graph and results:
            results = self._rrf_fusion(results, top_k * 2)

        reranker_used = False
        if use_reranker and results:
            results = await self._rerank(query, results, top_k)
            reranker_used = True

        final_results = results[:top_k]
        scores = [
            doc.get("rerank_score") or doc.get("rrf_score") or doc.get("score", 0)
            for doc in final_results
        ]
        latency_ms = int((time.time() - t0) * 1000)

        _retrieval_logs.appendleft(
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "query": query[:120],
                "top_k": top_k,
                "vector_hits": vector_count,
                "graph_hits": graph_count,
                "total_results": len(final_results),
                "reranker_used": reranker_used,
                "avg_score": round(sum(scores) / len(scores), 4) if scores else 0,
                "top_score": round(max(scores), 4) if scores else 0,
                "latency_ms": latency_ms,
                "sources": [doc.get("source", "unknown") for doc in final_results],
                "top_contents": [doc.get("content", "")[:80] for doc in final_results[:3]],
            }
        )
        return final_results

    async def _vector_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Run vector similarity search."""
        try:
            query_embedding = await embed_text(query)
            vector_store = self._get_vector_store()
            results = await vector_store.search(query_embedding, top_k=top_k)
            for result in results:
                result["source"] = "vector"
            return results
        except Exception as exc:
            logger.warning("Vector search failed: %s", exc)
            return []

    async def _graph_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Run graph search with light query normalization for natural questions."""
        try:
            graph_store = self._get_graph_store()
            raw_results: list[dict[str, Any]] = []
            for candidate in self._build_graph_search_queries(query):
                raw_results.extend(await graph_store.search_by_keyword(candidate, limit=top_k))

            docs: list[dict[str, Any]] = []
            seen_ids: set[str] = set()
            normalized_query = self._normalize_graph_query(query).lower()
            keywords = [token for token in normalized_query.split() if len(token) > 1]

            for item in raw_results:
                name = item.get("name", "")
                if not name or name in seen_ids:
                    continue
                seen_ids.add(name)

                props = item.get("props", {})
                description = props.get("description", "")
                content_parts = [f"名称: {name}"]
                if description:
                    content_parts.append(f"描述: {description}")

                combined_text = f"{name} {description}".lower()
                if keywords:
                    match_count = sum(1 for keyword in keywords if keyword in combined_text)
                    score = min(0.3 + (match_count / len(keywords)) * 0.7, 1.0)
                else:
                    score = 0.5

                docs.append(
                    {
                        "id": name,
                        "content": "\n".join(content_parts),
                        "metadata": {"types": item.get("types", [])},
                        "score": score,
                        "source": "graph",
                    }
                )

            docs.sort(key=lambda doc: doc.get("score", 0), reverse=True)
            return docs[:top_k]
        except Exception as exc:
            logger.warning("Graph search failed: %s", exc)
            return []

    def _build_graph_search_queries(self, query: str) -> list[str]:
        """Generate a few graph-friendly search phrases from a natural-language query."""
        candidates: list[str] = []
        seen: set[str] = set()

        def add_candidate(value: str) -> None:
            cleaned = self._normalize_graph_query(value)
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                candidates.append(cleaned)

        add_candidate(query)

        stripped = query
        for phrase in _GRAPH_NOISE_PHRASES:
            stripped = stripped.replace(phrase, " ")
        add_candidate(stripped)

        token_filtered = " ".join(
            token for token in self._normalize_graph_query(stripped).split() if token not in _GRAPH_NOISE_TOKENS
        )
        add_candidate(token_filtered)
        return candidates[:3]

    @staticmethod
    def _normalize_graph_query(query: str) -> str:
        """Normalize spacing and punctuation while preserving product-name tokens."""
        cleaned = _GRAPH_PUNCT_RE.sub(" ", query)
        cleaned = _GRAPH_SPACE_RE.sub(" ", cleaned).strip()
        return cleaned

    async def _rerank(self, query: str, results: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        """Optionally rerank candidate documents with the LLM reranker."""
        reranker = self._get_reranker()
        if not reranker:
            return results[:top_k]

        try:
            documents = [doc.get("content", "") for doc in results]
            reranked = await reranker.rerank(query, documents, top_k=top_k)

            reranked_results = []
            for item in reranked:
                index = item.get("index", 0)
                if index < len(results):
                    doc = results[index].copy()
                    doc["rerank_score"] = item.get("score", 0)
                    reranked_results.append(doc)
            return reranked_results
        except Exception as exc:
            logger.warning("Reranker failed, keeping pre-rerank order: %s", exc)
            return results[:top_k]

    def _rrf_fusion(self, results: list[dict[str, Any]], top_k: int, k: int = 60) -> list[dict[str, Any]]:
        """Fuse multi-source retrieval results with reciprocal rank fusion."""
        source_groups: dict[str, list[dict[str, Any]]] = {}
        for doc in results:
            source = doc.get("source", "unknown")
            source_groups.setdefault(source, []).append(doc)

        for docs in source_groups.values():
            docs.sort(key=lambda item: item.get("score", 0), reverse=True)

        doc_scores: dict[str, float] = {}
        doc_map: dict[str, dict[str, Any]] = {}

        for docs in source_groups.values():
            for rank, doc in enumerate(docs):
                doc_id = doc.get("id", str(rank))
                doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
                doc_map[doc_id] = doc

        fused: list[dict[str, Any]] = []
        for doc_id in sorted(doc_scores, key=doc_scores.get, reverse=True)[:top_k]:
            doc = doc_map[doc_id].copy()
            doc["rrf_score"] = doc_scores[doc_id]
            fused.append(doc)
        return fused
