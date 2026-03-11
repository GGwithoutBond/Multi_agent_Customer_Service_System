"""
会话相关 Schema
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """创建会话请求"""
    channel: str = Field(default="web", description="接入渠道")
    title: Optional[str] = Field(default=None, description="会话标题")
    metadata: Optional[dict] = Field(default=None, description="扩展元数据")


class ConversationUpdate(BaseModel):
    """更新会话请求"""
    title: Optional[str] = Field(default=None, max_length=100, description="会话标题")


class ConversationResponse(BaseModel):
    """会话响应"""
    id: UUID
    user_id: Optional[UUID] = None
    title: Optional[str] = None
    channel: str
    status: str
    summary: Optional[str] = None
    metadata: Optional[dict] = Field(default=None, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """会话列表项"""
    id: UUID
    title: Optional[str] = None
    channel: str
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}
