"""
公共 Schema 模式
通用的请求/响应模型
"""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseBase(BaseModel):
    """统一响应基类"""
    success: bool = True
    message: str = "ok"


class ResponseWithData(ResponseBase, Generic[T]):
    """带数据的统一响应"""
    data: Optional[T] = None


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(ResponseBase, Generic[T]):
    """分页响应"""
    data: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    message: str
    detail: Optional[Any] = None


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    version: str
    environment: str
    services: dict[str, str] = {}
