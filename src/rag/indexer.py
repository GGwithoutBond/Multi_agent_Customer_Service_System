"""
知识索引构建模块
将文档解析、切分、向量化后存入向量数据库和知识图谱
"""

import uuid
from typing import Any, Optional

from src.core.logging import get_logger
from src.rag.embeddings import embed_texts
from src.rag.graph_store import GraphStore
from src.rag.vector_store import VectorStore

logger = get_logger(__name__)


class KnowledgeIndexer:
    """知识库索引构建器"""

    def __init__(self):
        self.vector_store = VectorStore()
        self.graph_store = GraphStore()

    async def index_documents(
        self,
        documents: list[dict[str, Any]],
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> int:
        """
        索引文档列表

        Args:
            documents: 文档列表, 每项包含 content, metadata 字段
            chunk_size: 文本块大小
            chunk_overlap: 文本块重叠大小

        Returns:
            索引的文档块数
        """
        all_chunks = []
        for doc in documents:
            chunks = self._split_text(doc["content"], chunk_size, chunk_overlap)
            for chunk in chunks:
                all_chunks.append({
                    "id": str(uuid.uuid4()),
                    "content": chunk,
                    "metadata": doc.get("metadata", {}),
                })

        if not all_chunks:
            return 0

        # 批量向量化
        contents = [c["content"] for c in all_chunks]
        embeddings = await embed_texts(contents)

        # 存入向量数据库
        ids = [c["id"] for c in all_chunks]
        metadatas = [c["metadata"] for c in all_chunks]
        await self.vector_store.insert(ids, contents, embeddings, metadatas)

        logger.info("已索引 %d 个文档块", len(all_chunks))
        return len(all_chunks)

    async def index_entities(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> None:
        """
        索引知识图谱实体和关系

        Args:
            entities: 实体列表, 每项包含 type, properties 字段
            relationships: 关系列表
        """
        # 添加实体
        for entity in entities:
            await self.graph_store.add_entity(
                entity_type=entity["type"],
                properties=entity["properties"],
            )

        # 添加关系
        for rel in relationships:
            await self.graph_store.add_relationship(
                from_type=rel["from_type"],
                from_name=rel["from_name"],
                rel_type=rel["rel_type"],
                to_type=rel["to_type"],
                to_name=rel["to_name"],
                properties=rel.get("properties"),
            )

        logger.info("已索引 %d 个实体, %d 个关系", len(entities), len(relationships))

    def _split_text(self, text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
        """简单的文本切分"""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - chunk_overlap

        return chunks
