"""
Conversation schemas.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ConversationCreate(BaseModel):
    """Create conversation request."""

    channel: str = Field(default="web", description="Conversation channel")
    title: Optional[str] = Field(default=None, description="Conversation title")
    metadata: Optional[dict] = Field(default=None, description="Extended metadata")


class ConversationUpdate(BaseModel):
    """Update conversation request."""

    title: Optional[str] = Field(default=None, max_length=100, description="Conversation title")


class ConversationPinUpdate(BaseModel):
    """Pin/unpin conversation request."""

    is_pinned: bool = Field(..., description="Whether the conversation is pinned")


class ConversationBatchDeleteRequest(BaseModel):
    """Batch delete conversations request."""

    conversation_ids: list[UUID] = Field(..., min_length=1, max_length=200)

    @field_validator("conversation_ids")
    @classmethod
    def dedupe_ids(cls, value: list[UUID]) -> list[UUID]:
        unique: dict[UUID, None] = {}
        for item in value:
            unique[item] = None
        return list(unique.keys())


class ConversationBatchDeleteResponse(BaseModel):
    """Batch delete response payload."""

    requested: int
    deleted: int
    skipped: int
    skipped_ids: list[UUID] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    """Conversation response."""

    id: UUID
    user_id: Optional[UUID] = None
    title: Optional[str] = None
    channel: str
    status: str
    summary: Optional[str] = None
    is_pinned: bool = False
    metadata: Optional[dict] = Field(default=None, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    """Conversation list item."""

    id: UUID
    title: Optional[str] = None
    channel: str
    status: str
    is_pinned: bool = False
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}
