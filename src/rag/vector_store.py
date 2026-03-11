"""
向量存储模块 (Milvus)
管理向量的存储和检索
"""

from typing import Any, Optional

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """Milvus 向量存储"""

    def __init__(self):
        self.settings = get_settings()
        self._collection = None

    async def _get_collection(self):
        """获取或创建 Milvus 集合"""
        if self._collection is None:
            try:
                from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility

                connections.connect(
                    alias="default",
                    host=self.settings.MILVUS_HOST,
                    port=self.settings.MILVUS_PORT,
                )

                collection_name = self.settings.MILVUS_COLLECTION
                if utility.has_collection(collection_name):
                    self._collection = Collection(collection_name)
                else:
                    # 创建集合
                    fields = [
                        FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
                        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                        FieldSchema(name="metadata", dtype=DataType.JSON),
                        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.settings.EMBEDDING_DIMENSION),
                    ]
                    schema = CollectionSchema(fields=fields, description="知识库向量集合")
                    self._collection = Collection(name=collection_name, schema=schema)

                    # 创建索引
                    index_params = {
                        "metric_type": "COSINE",
                        "index_type": "IVF_FLAT",
                        "params": {"nlist": 128},
                    }
                    self._collection.create_index("embedding", index_params)

                self._collection.load()
            except Exception as e:
                logger.error("Milvus 连接/初始化失败: %s", e)
                raise

        return self._collection

    async def insert(
        self,
        ids: list[str],
        contents: list[str],
        embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
    ) -> None:
        """插入向量数据"""
        collection = await self._get_collection()
        if metadatas is None:
            metadatas = [{}] * len(ids)

        data = [ids, contents, metadatas, embeddings]
        collection.insert(data)
        collection.flush()
        logger.info("已插入 %d 条向量数据", len(ids))

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """向量相似度搜索"""
        try:
            collection = await self._get_collection()
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}

            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                expr=filters,
                output_fields=["content", "metadata"],
            )

            docs = []
            for hits in results:
                for hit in hits:
                    docs.append({
                        "id": hit.id,
                        "content": hit.entity.get("content", ""),
                        "metadata": hit.entity.get("metadata", {}),
                        "score": hit.score,
                    })
            return docs
        except Exception as e:
            logger.error("Milvus 搜索失败: %s", e)
            return []

    async def delete(self, ids: list[str]) -> None:
        """删除向量"""
        collection = await self._get_collection()
        expr = f'id in {ids}'
        collection.delete(expr)
        logger.info("已删除 %d 条向量数据", len(ids))
