"""
知识库管理 API 接口
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.api.deps import require_current_user
from src.schemas.common import ResponseBase, ResponseWithData
from src.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["知识库管理"])


class DocumentIndexRequest(BaseModel):
    """文档索引请求"""
    documents: list[dict[str, Any]] = Field(..., description="文档列表, 每项需包含 content 字段")
    chunk_size: int = Field(default=500, ge=100, le=2000, description="文本块大小")


class KnowledgeGraphIndexRequest(BaseModel):
    """知识图谱索引请求"""
    entities: list[dict[str, Any]] = Field(..., description="实体列表")
    relationships: list[dict[str, Any]] = Field(..., description="关系列表")


class SearchRequest(BaseModel):
    """知识搜索请求"""
    query: str = Field(..., min_length=1, max_length=512, description="搜索查询")
    top_k: int = Field(default=5, ge=1, le=20)
    use_vector: bool = True
    use_graph: bool = True


@router.post("/index/documents", response_model=ResponseWithData[dict])
async def index_documents(
    request: DocumentIndexRequest,
    _user_id=Depends(require_current_user),
):
    """索引文档到知识库"""
    service = KnowledgeService()
    count = await service.index_documents(
        documents=request.documents,
        chunk_size=request.chunk_size,
    )
    return ResponseWithData(data={"indexed_chunks": count})


@router.post("/index/graph", response_model=ResponseBase)
async def index_knowledge_graph(
    request: KnowledgeGraphIndexRequest,
    _user_id=Depends(require_current_user),
):
    """索引知识图谱"""
    service = KnowledgeService()
    await service.index_knowledge_graph(
        entities=request.entities,
        relationships=request.relationships,
    )
    return ResponseBase(message="知识图谱索引完成")


@router.post("/search", response_model=ResponseWithData[list[dict]])
async def search_knowledge(request: SearchRequest):
    """搜索知识库"""
    service = KnowledgeService()
    results = await service.search(
        query=request.query,
        top_k=request.top_k,
        use_vector=request.use_vector,
        use_graph=request.use_graph,
    )
    return ResponseWithData(data=results)
