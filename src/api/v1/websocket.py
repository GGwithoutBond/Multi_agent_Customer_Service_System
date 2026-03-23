"""
WebSocket 接口
实时双向通信
"""

import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.rate_limit import SlidingWindowRateLimiter
from src.core.config import get_settings
from src.core.security import decode_access_token
from src.core.logging import get_logger
from src.database.session import get_session_factory
from src.repositories.conversation_repo import ConversationRepository
from src.services.chat_service import ChatService

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])

# 活跃的 WebSocket 连接管理
active_connections: dict[str, WebSocket] = {}
_ws_connect_rate_limiter = SlidingWindowRateLimiter(window_seconds=60)
_ws_message_rate_limiter = SlidingWindowRateLimiter(window_seconds=60)


class WebSocketAuthError(Exception):
    """WebSocket 鉴权/授权失败。"""

    def __init__(self, code: int, reason: str):
        self.code = code
        self.reason = reason
        super().__init__(reason)


async def _authorize_websocket_connection(websocket: WebSocket, conversation_id: str) -> tuple[UUID, UUID]:
    """校验 token、会话归属与连接频率。"""
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketAuthError(code=4401, reason="缺少 token")

    try:
        payload = decode_access_token(token)
        user_id = UUID(str(payload.get("sub")))
    except Exception as exc:
        raise WebSocketAuthError(code=4401, reason="无效 token") from exc

    try:
        conversation_uuid = UUID(conversation_id)
    except ValueError as exc:
        raise WebSocketAuthError(code=4400, reason="无效 conversation_id") from exc

    settings = get_settings()
    client_ip = websocket.client.host if websocket.client else "unknown"
    connect_key = f"conn:{user_id}:{client_ip}"
    if not _ws_connect_rate_limiter.allow(connect_key, settings.WS_CONNECT_RATE_LIMIT_PER_MINUTE):
        raise WebSocketAuthError(code=4429, reason="连接过于频繁")

    factory = get_session_factory()
    async with factory() as db:
        conv_repo = ConversationRepository(db)
        conv = await conv_repo.get_by_id_for_user(conversation_uuid, user_id)
        if not conv:
            raise WebSocketAuthError(code=4404, reason="会话不存在或无权限")

    return user_id, conversation_uuid


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    """
    WebSocket 聊天接口

    消息格式:
    - 客户端发送: {"type": "message", "content": "用户输入"}
    - 服务端响应: {"type": "chunk", "content": "部分响应..."}
    - 服务端完成: {"type": "done", "message_id": "xxx"}
    - 服务端错误: {"type": "error", "message": "错误信息"}
    """
    try:
        user_id, conversation_uuid = await _authorize_websocket_connection(websocket, conversation_id)
    except WebSocketAuthError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

    await websocket.accept()
    connection_key = f"{conversation_id}:{id(websocket)}"
    active_connections[connection_key] = websocket

    logger.info("WebSocket 连接建立: %s user=%s", conversation_id, user_id)

    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "close":
                break

            if msg_type == "message":
                settings = get_settings()
                message_limit_key = f"msg:{user_id}:{connection_key}"
                if not _ws_message_rate_limiter.allow(message_limit_key, settings.WS_MESSAGE_RATE_LIMIT_PER_MINUTE):
                    await websocket.send_json({
                        "type": "error",
                        "message": "消息发送过于频繁，请稍后再试",
                    })
                    await websocket.close(code=4429, reason="消息频率超限")
                    break

                content = message.get("content", "")
                if not content:
                    await websocket.send_json({
                        "type": "error",
                        "message": "消息内容不能为空",
                    })
                    continue

                # 处理消息
                factory = get_session_factory()
                async with factory() as db:
                    try:
                        service = ChatService(db)
                        async for chunk in service.process_message_stream(
                            message=content,
                            conversation_id=conversation_uuid,
                            user_id=user_id,
                        ):
                            await websocket.send_json(chunk.model_dump(mode="json"))
                        await db.commit()
                    except Exception as e:
                        await db.rollback()
                        logger.error("WebSocket 消息处理失败: %s", e)
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                        })

    except WebSocketDisconnect:
        logger.info("WebSocket 连接断开: %s user=%s", conversation_id, user_id)
    except Exception as e:
        logger.error("WebSocket 异常: %s", e)
    finally:
        active_connections.pop(connection_key, None)
