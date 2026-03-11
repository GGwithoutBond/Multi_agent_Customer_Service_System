"""
向量化处理模块
文本 → 向量的转换
支持 OpenAI、DeepSeek、Qwen 兼容的 Embedding API
"""

import numpy as np
from typing import Optional

from langchain_openai import OpenAIEmbeddings

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

_embeddings: Optional[OpenAIEmbeddings] = None


def get_embeddings() -> Optional[OpenAIEmbeddings]:
    """获取 Embedding 模型单例"""
    global _embeddings
    if _embeddings is None:
        settings = get_settings()

        # 优先使用 Qwen，其次 OpenAI
        embedding_provider = getattr(settings, 'EMBEDDING_PROVIDER', 'openai')
        api_key = None
        api_base = None
        model = settings.EMBEDDING_MODEL

        if embedding_provider == 'qwen':
            api_key = getattr(settings, 'QWEN_API_KEY', None) or settings.OPENAI_API_KEY
            api_base = getattr(settings, 'QWEN_API_BASE', None) or settings.OPENAI_API_BASE
            logger.info(f"使用 Qwen Embedding: {api_base}")
        else:
            api_key = settings.OPENAI_API_KEY
            api_base = settings.OPENAI_API_BASE
            logger.info(f"使用 OpenAI Embedding")

        if not api_key:
            logger.warning("未配置任何 Embedding API Key，RAG 功能将不可用")
            return None

        params = {
            "model": model,
            "api_key": api_key,
        }
        if api_base:
            params["base_url"] = api_base

        # 指定向量维度（Qwen text-embedding-v3 默认 1024，需显式指定 1536）
        embedding_dim = getattr(settings, 'EMBEDDING_DIMENSION', None)
        if embedding_dim:
            params["dimensions"] = embedding_dim

        # Qwen 不兼容 langchain 的 token 长度检查（会发送 token 数组而非字符串）
        if embedding_provider == 'qwen':
            params["check_embedding_ctx_length"] = False

        _embeddings = OpenAIEmbeddings(**params)
    return _embeddings


async def embed_text(text: str) -> list[float]:
    """将单条文本转为向量"""
    embeddings = get_embeddings()
    if embeddings is None:
        # 返回随机向量作为占位
        dim = getattr(get_settings(), 'EMBEDDING_DIMENSION', 1536)
        return np.random.randn(dim).tolist()
    return await embeddings.aembed_query(text)


async def embed_texts(texts: list[str], batch_size: int = 6) -> list[list[float]]:
    """批量文本转向量（自动分批，适配 Qwen 等有 batch 限制的 API）"""
    embeddings = get_embeddings()
    if embeddings is None:
        dim = getattr(get_settings(), 'EMBEDDING_DIMENSION', 1536)
        return [np.random.randn(dim).tolist() for _ in texts]

    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = await embeddings.aembed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        logger.info("已完成 Embedding 批次 %d/%d", i // batch_size + 1, (len(texts) + batch_size - 1) // batch_size)
    return all_embeddings
