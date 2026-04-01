"""
Chat-related schemas.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    """Attachment payload for chat requests."""

    type: str = Field(..., description="attachment type: image / file / order / product")
    url: Optional[str] = Field(None, description="file URL (image/file)")
    name: Optional[str] = Field(None, description="file or entity name")
    size: Optional[int] = Field(None, description="file size in bytes")
    order_id: Optional[str] = Field(None, description="order ID")
    status: Optional[str] = Field(None, description="order status")
    product_id: Optional[str] = Field(None, description="product ID")
    price: Optional[float] = Field(None, description="product price")
    image: Optional[str] = Field(None, description="product image")


class ChatRequest(BaseModel):
    """Chat request."""

    conversation_id: Optional[UUID] = Field(None, description="conversation ID; auto-created when omitted")
    message: str = Field(..., min_length=1, max_length=4096, description="user message")
    attachments: Optional[List[Attachment]] = Field(None, description="attachment list")
    context: Optional[dict] = Field(None, description="extra context")
    persona_style: Optional[str] = Field(None, description="persona style: professional / friendly / technical")
    stream: bool = Field(default=False, description="use streaming response")
    web_search: bool = Field(default=False, description="enable web search")


class ChatResponse(BaseModel):
    """Chat response."""

    conversation_id: UUID
    message_id: UUID
    content: str
    intent: Optional[str] = None
    worker_type: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None


class ChatStreamChunk(BaseModel):
    """Streaming chat chunk."""

    type: str = Field(description="meta / chunk / thinking / tool_call / done / error / action_buttons")
    content: Optional[str] = None
    message_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    error: Optional[str] = None
    step: Optional[str] = Field(None, description="thinking/tool_call step description")
    actions: Optional[List[dict]] = Field(None, description="interactive actions for action_buttons type")
    metrics: Optional[dict[str, float | int | None]] = Field(
        None,
        description="stream metrics such as route_ms / worker_ms / ttfc_ms",
    )
    title: Optional[str] = Field(None, description="auto-generated conversation title (sent in done event)")


class WebSocketMessage(BaseModel):
    """WebSocket payload."""

    type: str = Field(description="message / ping / close")
    content: Optional[str] = None
    conversation_id: Optional[UUID] = None
