"""
自定义异常模块
定义系统中所有业务异常和错误类型
"""

from typing import Any, Optional


class BaseAppException(Exception):
    """应用基础异常"""

    def __init__(
        self,
        message: str = "服务内部错误",
        status_code: int = 500,
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


# ── 认证与授权 ──
class AuthenticationError(BaseAppException):
    def __init__(self, message: str = "认证失败"):
        super().__init__(message=message, status_code=401)


class AuthorizationError(BaseAppException):
    def __init__(self, message: str = "权限不足"):
        super().__init__(message=message, status_code=403)


# ── 资源相关 ──
class NotFoundError(BaseAppException):
    def __init__(self, resource: str = "资源", resource_id: str = ""):
        msg = f"{resource} 不存在" if not resource_id else f"{resource} [{resource_id}] 不存在"
        super().__init__(message=msg, status_code=404)


class ConflictError(BaseAppException):
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message=message, status_code=409)


# ── 请求相关 ──
class ValidationError(BaseAppException):
    def __init__(self, message: str = "请求参数无效", detail: Optional[Any] = None):
        super().__init__(message=message, status_code=422, detail=detail)


class RateLimitError(BaseAppException):
    def __init__(self, message: str = "请求过于频繁，请稍后再试"):
        super().__init__(message=message, status_code=429)


# ── 智能体相关 ──
class AgentError(BaseAppException):
    def __init__(self, message: str = "智能体处理异常"):
        super().__init__(message=message, status_code=500)


class AgentTimeoutError(AgentError):
    def __init__(self, message: str = "智能体处理超时"):
        super().__init__(message=message)


class WorkerNotFoundError(AgentError):
    def __init__(self, worker_type: str):
        super().__init__(message=f"Worker [{worker_type}] 不存在")


# ── LLM 相关 ──
class LLMError(BaseAppException):
    def __init__(self, message: str = "LLM 调用失败"):
        super().__init__(message=message, status_code=502)


class LLMRateLimitError(LLMError):
    def __init__(self, message: str = "LLM API 速率限制"):
        super().__init__(message=message)


# ── 外部服务 ──
class ExternalServiceError(BaseAppException):
    def __init__(self, service: str, message: str = ""):
        msg = f"外部服务 [{service}] 调用失败" + (f": {message}" if message else "")
        super().__init__(message=msg, status_code=502)


class DatabaseError(BaseAppException):
    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(message=message, status_code=500)


class CacheError(BaseAppException):
    def __init__(self, message: str = "缓存操作失败"):
        super().__init__(message=message, status_code=500)
