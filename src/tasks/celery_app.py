"""
Celery 应用实例
"""

from celery import Celery

from src.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "agent_system",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=[
        "src.tasks.knowledge_tasks",
        "src.tasks.memory_tasks",
        "src.tasks.notification_tasks",
    ],
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,  # 5 分钟软超时
    task_time_limit=600,       # 10 分钟硬超时
)
