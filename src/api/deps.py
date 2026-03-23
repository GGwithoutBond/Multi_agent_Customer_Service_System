"""
API 依赖注入
提供通用的依赖项给路由使用
"""

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings, get_settings
from src.core.security import decode_access_token
from src.database.session import get_db_session


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
) -> Optional[UUID]:
    """
    从 Authorization Header 中解析当前用户 ID

    Header 格式: Bearer <token>
    """
    if not authorization:
        return None

    try:
        scheme, token = authorization.split(" ", 1)
        if scheme.lower() != "bearer":
            return None
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        return UUID(user_id) if user_id else None
    except Exception:
        return None


async def require_current_user(
    authorization: Optional[str] = Header(None),
) -> UUID:
    """
    要求必须认证 - 返回当前用户 ID

    未认证时抛出 401 异常
    """
    user_id = await get_current_user_id(authorization)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证或认证已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


async def require_admin_user(
    user_id: UUID = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UUID:
    """
    要求管理员身份 - 返回当前用户 ID

    非管理员时抛出 403 异常。
    """
    from src.repositories.user_repo import UserRepository

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未认证或认证已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员角色",
        )
    return user_id


def get_settings_dep() -> Settings:
    """获取配置依赖"""
    return get_settings()
