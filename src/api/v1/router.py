"""
API v1 路由聚合
将所有子路由注册到统一的前缀下
"""

from fastapi import APIRouter

from src.api.v1.admin import router as admin_router
from src.api.v1.chat import router as chat_router
from src.api.v1.conversations import router as conversations_router
from src.api.v1.knowledge import router as knowledge_router
from src.api.v1.upload import router as upload_router
from src.api.v1.websocket import router as websocket_router

api_v1_router = APIRouter()

# 注册各模块路由
api_v1_router.include_router(chat_router)
api_v1_router.include_router(conversations_router)
api_v1_router.include_router(knowledge_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(upload_router)
api_v1_router.include_router(websocket_router)
