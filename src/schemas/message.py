"""
消息相关 Schema
"""

from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class MessageResponse(BaseModel):
    """消息响应"""
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    intent: Optional[str] = None
    worker_type: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    metadata_: Optional[dict] = Field(None, alias="metadata_")
    attachments: Optional[List[Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}

    @model_validator(mode="after")
    def extract_attachments(self):
        """从 metadata_ 提取 attachments"""
        if self.metadata_ and "attachments" in self.metadata_:
            self.attachments = self.metadata_["attachments"]
        return self


class FeedbackCreate(BaseModel):
    """反馈提交请求"""
    message_id: UUID = Field(..., description="消息 ID")
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    comment: Optional[str] = Field(None, max_length=1000, description="评论")


class FeedbackResponse(BaseModel):
    """反馈响应"""
    id: UUID
    message_id: UUID
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
