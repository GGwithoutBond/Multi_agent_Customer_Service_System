"""
聊天相关 Schema
"""

from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    """附件 (图片/文件/订单/商品)"""
    type: str = Field(..., description="attachment type: image / file / order / product")
    url: Optional[str] = Field(None, description="文件 URL (image/file)")
    name: Optional[str] = Field(None, description="文件名或名称")
    size: Optional[int] = Field(None, description="文件大小 (bytes)")
    # 订单相关
    order_id: Optional[str] = Field(None, description="订单 ID")
    status: Optional[str] = Field(None, description="订单状态")
    # 商品相关
    product_id: Optional[str] = Field(None, description="商品 ID")
    price: Optional[float] = Field(None, description="商品价格")
    image: Optional[str] = Field(None, description="商品图片")


class ChatRequest(BaseModel):
    """聊天请求"""
    conversation_id: Optional[UUID] = Field(None, description="会话 ID，为空则自动创建")
    message: str = Field(..., min_length=1, max_length=4096, description="用户消息")
    attachments: Optional[List[Attachment]] = Field(None, description="附件列表 (图片/文件/订单/商品)")
    context: Optional[dict] = Field(None, description="附加上下文信息")
    persona_style: Optional[str] = Field(None, description="客服风格 (professional / friendly / technical)")
    stream: bool = Field(default=False, description="是否使用流式响应")
    web_search: bool = Field(default=False, description="是否启用联网搜索")


class ChatResponse(BaseModel):
    """聊天响应"""
    conversation_id: UUID
    message_id: UUID
    content: str
    intent: Optional[str] = None
    worker_type: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None


class ChatStreamChunk(BaseModel):
    """流式聊天块"""
    type: str = Field(description="chunk / thinking / tool_call / done / error / action_buttons")
    content: Optional[str] = None
    message_id: Optional[UUID] = None
    error: Optional[str] = None
    step: Optional[str] = Field(None, description="过程步骤描述 (thinking/tool_call 类型使用)")
    actions: Optional[List[dict]] = Field(None, description="交互按钮列表 (action_buttons 类型使用)")


class WebSocketMessage(BaseModel):
    """WebSocket 消息"""
    type: str = Field(description="message / ping / close")
    content: Optional[str] = None
    conversation_id: Optional[UUID] = None
