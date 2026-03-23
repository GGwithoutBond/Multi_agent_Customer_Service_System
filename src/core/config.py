"""
应用配置管理模块
使用 Pydantic Settings 进行配置管理，支持环境变量和 .env 文件
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 基础配置 ──
    APP_NAME: str = "Multi-Agent Customer Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="development", description="运行环境: development/staging/production")
    LOG_LEVEL: str = "INFO"

    # ── API 配置 ──
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: list[str] = ["*"]
    API_RATE_LIMIT: int = 60  # 每分钟请求数

    # ── 安全配置 ──
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 小时
    ALGORITHM: str = "HS256"

    # ── PostgreSQL 配置 ──
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "chatdb"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Redis 配置 ──
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── RabbitMQ 配置 ──
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

    @property
    def RABBITMQ_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"

    # ── Neo4j 配置 ──
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ── Milvus 配置 ──
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "knowledge_base"

    # ── LLM 配置 ──
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_API_BASE: Optional[str] = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    DEFAULT_LLM_PROVIDER: str = "deepseek"  # openai / anthropic / deepseek
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 4096

    # ── Streaming / latency behavior ──
    ENABLE_ASYNC_POSTPROCESS: bool = Field(
        default=True,
        description="Whether to run memory/summary/cache post-processing in background after stream done.",
    )
    ENABLE_SYNC_FIRST_TURN_SUMMARY: bool = Field(
        default=False,
        description="Whether first-turn summary generation blocks stream completion.",
    )
    ENABLE_SYNC_QUALITY_REVIEW: bool = Field(
        default=True,
        description="Whether to run quality review on the critical path.",
    )
    SYNC_QUALITY_REVIEW_RISK_ONLY: bool = Field(
        default=True,
        description="When true, only complaint/high-risk requests run sync quality review.",
    )
    ENABLE_ASYNC_QUALITY_REVIEW: bool = Field(
        default=True,
        description="Whether to run async quality review for non-risk requests.",
    )

    # ── MCP 配置 ──
    MCP_ENABLED: bool = Field(default=False, description="是否启用 MCP 增强模式（需要 MCP 服务器运行）")

    # ── 记忆配置 ──
    MEMORY_MAX_TOKENS: int = 4000
    MEMORY_MAX_TURNS: int = 10
    MEMORY_SUMMARY_THRESHOLD: int = 8  # 超过此轮次后触发摘要压缩

    # ── Embedding 配置 ──
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_PROVIDER: str = "openai"  # openai / qwen

    # ── Qwen 配置 (用于 Embedding) ──
    QWEN_API_KEY: Optional[str] = None
    QWEN_API_BASE: Optional[str] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ── Tavily 搜索 API ──
    TAVILY_API_KEY: Optional[str] = None

    # ── 缓存配置 ──
    ENABLE_SEMANTIC_CACHE: bool = Field(default=False, description="是否开启对话语义缓存")

@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
