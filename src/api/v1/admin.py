"""
管理后台 API 接口
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_admin_user, require_current_user
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


# ==========================================
# Admin Dashboard APIs (Real Data)
# ==========================================

@router.get("/admin/dashboard/metrics")
async def get_dashboard_metrics(
    _admin_user_id: UUID = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """获取后台看板核心指标 (Real Data)"""
    from sqlalchemy import select, func
    from src.models.message import Message, MessageRole
    from src.models.user import User

    # 请求总数 (User messages)
    total_requests_stmt = select(func.count(Message.id)).where(Message.role == MessageRole.USER)
    total_requests = (await db.execute(total_requests_stmt)).scalar() or 0

    # 活跃用户数
    active_users_stmt = select(func.count(User.id)).where(User.is_active == True)
    active_users = (await db.execute(active_users_stmt)).scalar() or 0

    # 平均延迟 (Assistant messages)
    avg_latency_stmt = select(func.avg(Message.latency_ms)).where(Message.role == MessageRole.ASSISTANT, Message.latency_ms.is_not(None))
    avg_latency_val = (await db.execute(avg_latency_stmt)).scalar()
    average_latency = f"{int(avg_latency_val)}ms" if avg_latency_val else "0ms"

    # 活动模型数
    active_models_stmt = select(func.count(func.distinct(Message.worker_type))).where(Message.worker_type.is_not(None))
    active_models = (await db.execute(active_models_stmt)).scalar() or 0

    return {
        "status": "success",
        "data": {
            "totalRequests": total_requests,
            "activeUsers": active_users,
            "averageLatency": average_latency,
            "activeModels": active_models
        }
    }


@router.get("/admin/models/logs")
async def get_model_logs(
    _admin_user_id: UUID = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """获取大模型调用流水日志 (Real Data)"""
    from sqlalchemy import select
    from src.models.message import Message, MessageRole

    # 获取最近的 Assistant 回复作为日志主体
    stmt = select(Message).where(Message.role == MessageRole.ASSISTANT).order_by(Message.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    data = []
    for msg in messages:
        data.append({
            "id": str(msg.id),
            "timestamp": msg.created_at.strftime("%Y-%m-%d %H:%M:%S") if msg.created_at else "",
            "modelName": msg.worker_type or "unknown",
            "promptSnippet": "关联的提示词请在会话中查看", # 简化处理，不连表查询上文
            "outputSnippet": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
            "tokens": msg.tokens_used or 0,
            "latency": msg.latency_ms or 0
        })

    return {
        "status": "success",
        "data": data,
        "total": len(data)
    }


@router.get("/admin/middleware/status")
async def get_middleware_status(
    _admin_user_id: UUID = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db_session),
):
    """获取中间件详细状态监控 (Real Data)"""
    from sqlalchemy import text
    from src.database.redis import get_redis

    # Redis Status
    redis_status = {"status": "unhealthy", "memoryUsed": "0MB", "memoryPercentage": 0, "connections": 0, "uptime": "0d"}
    try:
        redis = get_redis()
        info = await redis.info()
        redis_status["status"] = "healthy"
        redis_status["memoryUsed"] = info.get("used_memory_human", "0MB")
        redis_status["connections"] = info.get("connected_clients", 0)
        uptime_days = info.get("uptime_in_days", 0)
        redis_status["uptime"] = f"{uptime_days}d"
        # 简单估算 percentage (假设1GB Max)
        used_memory = info.get("used_memory", 0)
        redis_status["memoryPercentage"] = min(100, int((used_memory / (1024 * 1024 * 1024)) * 100))
    except Exception as e:
        print(f"获取 Redis 状态失败: {e}")

    # Postgres Status
    pg_status = {"status": "unhealthy", "activeConnections": 0, "maxConnections": 100, "databaseSize": "0MB", "queriesPerSecond": 0}
    try:
        # Number of active connections
        conn_res = await db.execute(text("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"))
        pg_status["activeConnections"] = conn_res.scalar() or 0

        # Max connections
        max_res = await db.execute(text("SHOW max_connections"))
        pg_status["maxConnections"] = int(max_res.scalar() or 100)

        # DB Size
        size_res = await db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))"))
        pg_status["databaseSize"] = size_res.scalar() or "0MB"

        pg_status["status"] = "healthy"
    except Exception as e:
        print(f"获取 PostgreSQL 状态失败: {e}")

    return {
        "status": "success",
        "data": {
            "redis": redis_status,
            "postgres": pg_status
        }
    }


@router.get("/admin/rag/status")
async def get_rag_status(
    _admin_user_id: UUID = Depends(require_admin_user),
):
    """获取 RAG 知识库与图谱检索服务的状态及指标 (Real Data)"""
    from src.rag.vector_store import VectorStore
    from src.rag.graph_store import GraphStore

    rag_data = {
        "vector_store": {"status": "unhealthy", "collection_name": "", "dimension": 0, "total_vectors": 0},
        "graph_store": {"status": "unhealthy", "total_nodes": 0, "total_relations": 0}
    }

    # 拉取 Milvus 数据
    try:
        vs = VectorStore()
        collection = await vs._get_collection()
        rag_data["vector_store"]["status"] = "healthy"
        rag_data["vector_store"]["collection_name"] = vs.settings.MILVUS_COLLECTION
        rag_data["vector_store"]["dimension"] = vs.settings.EMBEDDING_DIMENSION
        rag_data["vector_store"]["total_vectors"] = collection.num_entities
    except Exception as e:
        print(f"获取 RAG Milvus 状态失败: {e}")

    # 拉取 Neo4j 数据
    try:
        gs = GraphStore()
        
        # Count nodes
        nodes_res = await gs.query("MATCH (n) RETURN count(n) as count")
        total_nodes = nodes_res[0]["count"] if nodes_res else 0
        
        # Count relationships
        rels_res = await gs.query("MATCH ()-[r]->() RETURN count(r) as count")
        total_relations = rels_res[0]["count"] if rels_res else 0
        
        rag_data["graph_store"]["status"] = "healthy"
        rag_data["graph_store"]["total_nodes"] = total_nodes
        rag_data["graph_store"]["total_relations"] = total_relations
        await gs.close()
    except Exception as e:
        print(f"获取 RAG Neo4j 状态失败: {e}")

    return {
        "status": "success",
        "data": rag_data
    }


@router.get("/admin/rag/retrieval-logs")
async def get_rag_retrieval_logs(
    _admin_user_id: UUID = Depends(require_admin_user),
):
    """获取 RAG 检索质量指标日志（最近 200 条）"""
    from src.rag.retriever import get_retrieval_logs

    logs = get_retrieval_logs()

    # 聚合统计
    if logs:
        avg_score = round(sum(l["avg_score"] for l in logs) / len(logs), 4)
        avg_latency = round(sum(l["latency_ms"] for l in logs) / len(logs), 1)
        avg_results = round(sum(l["total_results"] for l in logs) / len(logs), 1)
        total_vector = sum(l["vector_hits"] for l in logs)
        total_graph = sum(l["graph_hits"] for l in logs)
        reranker_ratio = round(sum(1 for l in logs if l["reranker_used"]) / len(logs) * 100, 1)
    else:
        avg_score = 0
        avg_latency = 0
        avg_results = 0
        total_vector = 0
        total_graph = 0
        reranker_ratio = 0

    return {
        "status": "success",
        "data": {
            "logs": logs[:100],  # 前端最多展示 100 条
            "summary": {
                "total_queries": len(logs),
                "avg_relevance_score": avg_score,
                "avg_latency_ms": avg_latency,
                "avg_results_per_query": avg_results,
                "total_vector_hits": total_vector,
                "total_graph_hits": total_graph,
                "reranker_usage_percent": reranker_ratio,
            }
        }
    }
