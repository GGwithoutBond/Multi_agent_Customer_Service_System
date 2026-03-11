"""
知识库构建异步任务
"""

import asyncio
from typing import Any

from src.core.logging import get_logger
from src.tasks.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="tasks.build_knowledge_index")
def build_knowledge_index(documents: list[dict[str, Any]], chunk_size: int = 500) -> dict:
    """
    异步构建知识库索引

    Args:
        documents: 文档列表
        chunk_size: 文档块大小
    """
    logger.info("开始构建知识库索引, 文档数: %d", len(documents))

    async def _run():
        from src.services.knowledge_service import KnowledgeService
        service = KnowledgeService()
        count = await service.index_documents(documents, chunk_size=chunk_size)
        return count

    count = asyncio.get_event_loop().run_until_complete(_run())
    logger.info("知识库索引构建完成, 索引块数: %d", count)
    return {"status": "completed", "indexed_chunks": count}


@celery_app.task(name="tasks.build_knowledge_graph")
def build_knowledge_graph(
    entities: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> dict:
    """异步构建知识图谱"""
    logger.info("开始构建知识图谱, 实体数: %d, 关系数: %d", len(entities), len(relationships))

    async def _run():
        from src.services.knowledge_service import KnowledgeService
        service = KnowledgeService()
        await service.index_knowledge_graph(entities, relationships)

    asyncio.get_event_loop().run_until_complete(_run())
    logger.info("知识图谱构建完成")
    return {"status": "completed", "entities": len(entities), "relationships": len(relationships)}
