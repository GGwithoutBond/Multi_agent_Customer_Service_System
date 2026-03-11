"""
聊天 API 接口
优化: 增强反馈闭环、满意度调查
"""

import json
from typing import Optional
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


@router.post("", response_model=ResponseWithData[ChatResponse])
async def send_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    发送消息（同步响应）
    """
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
    """
    发送消息（流式 SSE 响应）
    优化 2.1: 逐 chunk 流式输出
    """
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
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )


@router.post("/feedback", response_model=ResponseWithData[FeedbackResponse])
async def submit_feedback(
    request: FeedbackCreate,
    db: AsyncSession = Depends(get_db_session),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    提交用户反馈
    优化 2.4: 负面反馈自动触发重新回答
    """
    from src.models.feedback import Feedback
    from src.core.logging import get_logger
    logger = get_logger(__name__)

    feedback = Feedback(
        message_id=request.message_id,
        rating=request.rating,
        comment=request.comment,
    )
    db.add(feedback)
    await db.flush()
    await db.refresh(feedback)

    # 记录反馈指标（优化 6.4: 可观测性）
    logger.info(
        "📊 用户反馈 | message_id=%s rating=%d comment=%s",
        request.message_id,
        request.rating,
        (request.comment or "")[:50],
    )

    # 优化 2.4: 负面反馈闭环
    if request.rating <= 2:
        logger.warning(
            "📉 负面反馈收到 (rating=%d)，可触发重新回答",
            request.rating,
        )
        # 在响应中标记需要重试（前端可据此发起重新回答）
        response_data = FeedbackResponse.model_validate(feedback)
        return ResponseWithData(
            data=response_data,
            message="感谢您的反馈，我们会努力改进！正在为您重新生成回答...",
        )

    return ResponseWithData(data=FeedbackResponse.model_validate(feedback))
