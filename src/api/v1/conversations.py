"""
会话管理 API 接口
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user_id, require_current_user
from src.database.session import get_db_session
from src.schemas.common import PaginatedResponse, ResponseWithData
from src.schemas.conversation import ConversationCreate, ConversationResponse, ConversationUpdate
from src.schemas.message import MessageResponse
from src.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["会话管理"])


@router.post("", response_model=ResponseWithData[ConversationResponse])
async def create_conversation(
    request: ConversationCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """创建新会话"""
    service = ConversationService(db)
    conv = await service.create_conversation(
        user_id=user_id,
        channel=request.channel,
        metadata=request.metadata,
    )
    return ResponseWithData(data=ConversationResponse.model_validate(conv))


@router.get("", response_model=PaginatedResponse[ConversationResponse])
async def list_conversations(
    status: Optional[str] = Query(None, description="会话状态过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(require_current_user),
):
    """获取当前用户的会话列表"""
    service = ConversationService(db)
    conversations, total = await service.list_conversations(
        user_id=user_id,
        status=status,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size
    items = [ConversationResponse.model_validate(c) for c in conversations]

    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{conversation_id}", response_model=ResponseWithData[ConversationResponse])
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """获取会话详情"""
    service = ConversationService(db)
    conv = await service.get_conversation(conversation_id)
    return ResponseWithData(data=ConversationResponse.model_validate(conv))


@router.get("/{conversation_id}/messages", response_model=ResponseWithData[list[MessageResponse]])
async def get_conversation_messages(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """获取会话消息历史"""
    service = ConversationService(db)
    conv = await service.get_conversation_with_messages(conversation_id)
    messages = [MessageResponse.model_validate(m) for m in conv.messages]
    return ResponseWithData(data=messages)


@router.delete("/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """删除会话（物理删除）"""
    service = ConversationService(db)
    await service.delete_conversation(conversation_id)
    return {"code": 0, "message": "删除成功"}


@router.put("/{conversation_id}", response_model=ResponseWithData[ConversationResponse])
async def update_conversation(
    conversation_id: UUID,
    request: ConversationUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新会话"""
    service = ConversationService(db)
    update_data = request.model_dump(exclude_unset=True)
    if update_data:
        conv = await service.conv_repo.update_by_id(conversation_id, **update_data)
        return ResponseWithData(data=ConversationResponse.model_validate(conv))
    return await get_conversation(conversation_id, db)
