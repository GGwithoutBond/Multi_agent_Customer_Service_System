"""
语义缓存 (Semantic Cache) 层
降低高频相似问题的 LLM 调用延迟和成本
"""

import time
from typing import Any, Optional
import numpy as np

from src.core.logging import get_logger
from src.rag.embeddings import embed_text

logger = get_logger(__name__)


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """计算余弦相似度"""
    vec1 = np.array(v1)
    vec2 = np.array(v2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(np.dot(vec1, vec2) / (norm1 * norm2))


# 包含以下关键词的查询不走缓存（事务性/操作性请求）
SKIP_CACHE_KEYWORDS = ["退货", "退款", "退换", "退回", "取消订单", "投诉", "确认退货", "取消退货"]


class SemanticCache:
    """
    语义缓存实现
    支持基于内存的最近使用缓存。
    可配置阈值 (threshold) 决定命中条件。
    事务性查询（退货/退款等）不走缓存。
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SemanticCache, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, threshold: float = 0.95, capacity: int = 1000, ttl_seconds: int = 86400):
        if self.initialized:
            return
            
        self.threshold = threshold
        self.capacity = capacity
        self.ttl_seconds = ttl_seconds
        
        # 内部结构: [{"query": str, "embedding": List[float], "response": str, "timestamp": float}]
        self.cache: list[dict[str, Any]] = []
        self.initialized = True
        logger.info("语义缓存初始化成功 (阈值: %s, 容量: %d)", self.threshold, self.capacity)

    @staticmethod
    def _should_skip_cache(query: str) -> bool:
        """判断是否应该跳过缓存（事务性请求）"""
        return any(kw in query for kw in SKIP_CACHE_KEYWORDS)

    def clear(self):
        """清空全部缓存"""
        self.cache.clear()
        logger.info("语义缓存已清空")

    def invalidate(self, keyword: str):
        """删除包含指定关键词的缓存项"""
        before = len(self.cache)
        self.cache = [item for item in self.cache if keyword not in item.get("query", "")]
        removed = before - len(self.cache)
        if removed:
            logger.info("已清除 %d 条包含 '%s' 的缓存", removed, keyword)

    async def get(self, query: str) -> Optional[str]:
        """
        检索缓存
        如果 query 的 embedding 和缓存中的某项余弦相似度 >= threshold，则命中缓存。
        事务性查询自动跳过。
        """
        if not self.cache:
            return None

        # 事务性查询不走缓存
        if self._should_skip_cache(query):
            logger.debug("跳过缓存 (事务性查询): %s", query[:50])
            return None
            
        try:
            # 1. 过滤过期项
            now = time.time()
            self.cache = [item for item in self.cache if now - item["timestamp"] < self.ttl_seconds]
            
            if not self.cache:
                return None
                
            # 2. 计算当前 query 的 embedding
            query_embedding = await embed_text(query)
            
            # 3. 寻找最相似的缓存
            best_match = None
            max_score = 0.0
            
            for item in self.cache:
                score = cosine_similarity(query_embedding, item["embedding"])
                if score > max_score:
                    max_score = score
                    best_match = item
                    
            if best_match and max_score >= self.threshold:
                logger.info("⚡ 命中语义缓存 (相似度: %.3f): %s -> %s", max_score, query, best_match["query"])
                # 更新访问时间 (实现 LRU 的简化版)
                best_match["timestamp"] = now
                return best_match["response"]
                
            return None
            
        except Exception as e:
            logger.warning("语义缓存查询失败: %s", e)
            return None

    async def set(self, query: str, response: str) -> None:
        """
        写入缓存
        事务性查询不写入缓存。
        """
        # 事务性查询不写入缓存
        if self._should_skip_cache(query):
            logger.debug("跳过缓存写入 (事务性查询): %s", query[:50])
            return

        try:
            query_embedding = await embed_text(query)
            
            now = time.time()
            # 检查是否已有高度相似的，如果有则更新，否则新增
            for item in self.cache:
                score = cosine_similarity(query_embedding, item["embedding"])
                if score >= 0.99: # 近似完全一致
                    item["response"] = response
                    item["timestamp"] = now
                    return
            
            # 检查容量
            if len(self.cache) >= self.capacity:
                # 简单 LRU: 移除最旧的
                self.cache.sort(key=lambda x: x["timestamp"])
                self.cache.pop(0)
                
            self.cache.append({
                "query": query,
                "embedding": query_embedding,
                "response": response,
                "timestamp": now
            })
            
            logger.debug("写入语义缓存: %s (当前缓存数: %d)", query, len(self.cache))
            
        except Exception as e:
            logger.error("写入语义缓存失败: %s", e)
