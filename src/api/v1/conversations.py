"""
Conversation management API.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user_id, require_current_user
from src.database.session import get_db_session
from src.schemas.common import PaginatedResponse, ResponseWithData
from src.schemas.conversation import (
    ConversationBatchDeleteRequest,
    ConversationBatchDeleteResponse,
    ConversationCreate,
    ConversationPinUpdate,
    ConversationResponse,
    ConversationUpdate,
)
from src.schemas.message import MessageHistoryResponse, MessageResponse
from src.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversation"])


@router.post("", response_model=ResponseWithData[ConversationResponse])
async def create_conversation(
    request: ConversationCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    service = ConversationService(db)
    conv = await service.create_conversation(
        user_id=user_id,
        channel=request.channel,
        metadata=request.metadata,
    )
    return ResponseWithData(data=ConversationResponse.model_validate(conv))


@router.get("", response_model=PaginatedResponse[ConversationResponse])
async def list_conversations(
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(require_current_user),
):
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
    user_id: UUID = Depends(require_current_user),
):
    service = ConversationService(db)
    conv = await service.get_conversation_for_user(conversation_id, user_id)
    return ResponseWithData(data=ConversationResponse.model_validate(conv))


@router.get("/{conversation_id}/messages", response_model=ResponseWithData[list[MessageResponse]])
async def get_conversation_messages(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(require_current_user),
):
    service = ConversationService(db)
    conv = await service.get_conversation_with_messages_for_user(conversation_id, user_id)
    messages = [MessageResponse.model_validate(m) for m in conv.messages]
    return ResponseWithData(data=messages)


@router.get(
    "/{conversation_id}/messages/history",
    response_model=ResponseWithData[MessageHistoryResponse],
)
async def get_conversation_messages_history(
    conversation_id: UUID,
    before_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(require_current_user),
):
    service = ConversationService(db)
    messages, has_more, next_before_id = await service.get_messages_history_for_user(
        conversation_id=conversation_id,
        user_id=user_id,
        before_id=before_id,
        limit=limit,
    )
    payload = MessageHistoryResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        has_more=has_more,
        next_before_id=next_before_id,
    )
    return ResponseWithData(data=payload)


@router.delete("/{conversation_id}")
async def delete_conversation_endpoint(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(require_current_user),
):
    service = ConversationService(db)
    await service.delete_conversation_for_user(conversation_id, user_id)
    return {"code": 0, "message": "删除成功"}


@router.post("/batch-delete", response_model=ResponseWithData[ConversationBatchDeleteResponse])
async def batch_delete_conversations(
    request: ConversationBatchDeleteRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(require_current_user),
):
    service = ConversationService(db)
    summary = await service.batch_delete_for_user(
        user_id=user_id,
        conversation_ids=request.conversation_ids,
    )
    return ResponseWithData(data=ConversationBatchDeleteResponse(**summary))


@router.put("/{conversation_id}", response_model=ResponseWithData[ConversationResponse])
async def update_conversation(
    conversation_id: UUID,
    request: ConversationUpdate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(require_current_user),
):
    service = ConversationService(db)
    update_data = request.model_dump(exclude_unset=True)
    if update_data:
        conv = await service.update_conversation_for_user(conversation_id, user_id, **update_data)
        return ResponseWithData(data=ConversationResponse.model_validate(conv))
    return await get_conversation(conversation_id, db, user_id)


@router.patch("/{conversation_id}/pin", response_model=ResponseWithData[ConversationResponse])
async def update_conversation_pin(
    conversation_id: UUID,
    request: ConversationPinUpdate,
    db: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(require_current_user),
):
    service = ConversationService(db)
    conv = await service.update_pin_for_user(
        conversation_id=conversation_id,
        user_id=user_id,
        is_pinned=request.is_pinned,
    )
    return ResponseWithData(data=ConversationResponse.model_validate(conv))
