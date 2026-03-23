"""
聊天 API 接口
"""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user_id
from src.database.session import get_db_session
from src.schemas.chat import ChatRequest, ChatResponse
from src.schemas.common import ResponseWithData
from src.schemas.message import FeedbackCreate, FeedbackResponse
from src.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["聊天"])


@router.get("/orders/options", response_model=ResponseWithData[list[dict[str, Any]]])
async def get_order_options(
    db: AsyncSession = Depends(get_db_session),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """获取前端订单下拉选项。"""
    service = ChatService(db)
    data = await service.get_available_orders(user_id)
    return ResponseWithData(data=data)


@router.get("/products/options", response_model=ResponseWithData[list[dict[str, Any]]])
async def get_product_options(
    db: AsyncSession = Depends(get_db_session),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """获取前端商品下拉选项。"""
    service = ChatService(db)
    data = await service.get_available_products(user_id)
    return ResponseWithData(data=data)


@router.post("", response_model=ResponseWithData[ChatResponse])
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """发送同步聊天消息。"""
    service = ChatService(db)
    attachments_data = None
    if request.attachments:
        attachments_data = [a.model_dump(exclude_none=True) for a in request.attachments]
    context = request.context or {}
    if request.persona_style:
        context["persona_style"] = request.persona_style

    result = await service.process_message(
        message=request.message,
        conversation_id=request.conversation_id,
        user_id=user_id,
        context=context,
        attachments=attachments_data,
        web_search=request.web_search,
    )
    return ResponseWithData(data=result)


@router.post("/stream")
async def send_message_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """发送流式聊天消息（SSE）。"""
    service = ChatService(db)
    attachments_data = None
    if request.attachments:
        attachments_data = [a.model_dump(exclude_none=True) for a in request.attachments]

    context = request.context or {}
    if request.persona_style:
        context["persona_style"] = request.persona_style

    async def event_generator():
        async for chunk in service.process_message_stream(
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=user_id,
            context=context,
            attachments=attachments_data,
            web_search=request.web_search,
        ):
            data = chunk.model_dump_json()
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/feedback", response_model=ResponseWithData[FeedbackResponse])
async def submit_feedback(
    request: FeedbackCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """提交用户反馈。"""
    from src.core.logging import get_logger
    from src.models.feedback import Feedback

    logger = get_logger(__name__)

    feedback = Feedback(
        message_id=request.message_id,
        rating=request.rating,
        comment=request.comment,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)

    logger.info(
        "用户反馈 | message_id=%s rating=%d comment=%s",
        request.message_id,
        request.rating,
        (request.comment or "")[:50],
    )

    if request.rating <= 2:
        logger.warning("收到负面反馈 (rating=%d)，可触发重新回答", request.rating)
        response_data = FeedbackResponse.model_validate(feedback)
        return ResponseWithData(
            data=response_data,
            message="感谢您的反馈，我们会持续改进，正在为您重新生成回答。",
        )

    return ResponseWithData(data=FeedbackResponse.model_validate(feedback))
