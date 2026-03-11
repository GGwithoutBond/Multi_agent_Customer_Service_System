"""
知识库服务
管理知识库的索引和检索
"""

from typing import Any, Optional

from src.core.logging import get_logger
from src.rag.indexer import KnowledgeIndexer
from src.rag.retriever import HybridRetriever

logger = get_logger(__name__)


class KnowledgeService:
    """知识库管理服务"""

    def __init__(self):
        self.indexer = KnowledgeIndexer()
        self.retriever = HybridRetriever()

    async def index_documents(
        self,
        documents: list[dict[str, Any]],
        chunk_size: int = 500,
    ) -> int:
        """索引文档"""
        count = await self.indexer.index_documents(documents, chunk_size=chunk_size)
        logger.info("索引完成, 共 %d 个文档块", count)
        return count

    async def index_knowledge_graph(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> None:
        """索引知识图谱"""
        await self.indexer.index_entities(entities, relationships)
        logger.info("知识图谱索引完成")

    async def search(
        self,
        query: str,
        top_k: int = 5,
        use_vector: bool = True,
        use_graph: bool = True,
    ) -> list[dict[str, Any]]:
        """搜索知识库"""
        results = await self.retriever.retrieve(
            query, top_k=top_k,
            use_vector=use_vector, use_graph=use_graph,
        )
        return results
