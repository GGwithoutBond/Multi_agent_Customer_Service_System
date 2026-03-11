"""
管理后台 API 接口
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_current_user
from src.core.config import get_settings
from src.database.session import get_db_session
from src.schemas.common import HealthCheckResponse, ResponseWithData
from src.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(tags=["管理"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """健康检查"""
    settings = get_settings()

    services = {}

    # 检查 Redis
    try:
        from src.database.redis import get_redis
        redis = get_redis()
        await redis.ping()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"

    # 检查 PostgreSQL
    try:
        from src.database.postgres import get_engine
        from sqlalchemy import text
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["postgres"] = "healthy"
    except Exception:
        services["postgres"] = "unhealthy"

    return HealthCheckResponse(
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        services=services,
    )


@router.post("/auth/register", response_model=ResponseWithData[UserResponse])
async def register(
    request: UserCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """用户注册"""
    from src.core.security import hash_password
    from src.models.user import User
    from src.repositories.user_repo import UserRepository

    repo = UserRepository(db)

    # 检查用户名是否已存在
    existing = await repo.get_by_username(request.username)
    if existing:
        from src.core.exceptions import ConflictError
        raise ConflictError("用户名已存在")

    user = User(
        username=request.username,
        hashed_password=hash_password(request.password),
        email=request.email,
        display_name=request.display_name,
    )
    user = await repo.create(user)

    return ResponseWithData(data=UserResponse.model_validate(user))


@router.post("/auth/login", response_model=ResponseWithData[TokenResponse])
async def login(
    request: UserLogin,
    db: AsyncSession = Depends(get_db_session),
):
    """用户登录"""
    from src.core.exceptions import AuthenticationError
    from src.core.security import create_access_token, verify_password
    from src.repositories.user_repo import UserRepository

    repo = UserRepository(db)
    user = await repo.get_by_username(request.username)

    if not user or not verify_password(request.password, user.hashed_password):
        raise AuthenticationError("用户名或密码错误")

    if not user.is_active:
        raise AuthenticationError("账户已被禁用")

    access_token = create_access_token(subject=str(user.id))

    return ResponseWithData(
        data=TokenResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )
    )


@router.get("/users/me", response_model=ResponseWithData[UserResponse])
async def get_current_user(
    user_id: UUID = Depends(require_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """获取当前用户信息"""
    from src.core.exceptions import NotFoundError
    from src.repositories.user_repo import UserRepository

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise NotFoundError("用户", str(user_id))

    return ResponseWithData(data=UserResponse.model_validate(user))
