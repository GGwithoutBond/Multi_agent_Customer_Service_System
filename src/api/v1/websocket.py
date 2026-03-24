"""
WebSocket endpoints.
"""

import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.api.rate_limit import SlidingWindowRateLimiter
from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.security import decode_access_token
from src.database.session import get_session_factory
from src.repositories.conversation_repo import ConversationRepository
from src.repositories.user_repo import UserRepository
from src.services.chat_service import ChatService
from src.services.connection_pool import get_connection_pool

logger = get_logger(__name__)
router = APIRouter(tags=["websocket"])

_ws_connect_rate_limiter = SlidingWindowRateLimiter(window_seconds=60)
_ws_message_rate_limiter = SlidingWindowRateLimiter(window_seconds=60)


class WebSocketAuthError(Exception):
    """WebSocket authentication/authorization error."""

    def __init__(self, code: int, reason: str):
        self.code = code
        self.reason = reason
        super().__init__(reason)


def _decode_user_id_from_token(token: str) -> UUID:
    try:
        payload = decode_access_token(token)
        return UUID(str(payload.get("sub")))
    except Exception as exc:
        raise WebSocketAuthError(code=4401, reason="invalid token") from exc


async def _authorize_websocket_connection(websocket: WebSocket, conversation_id: str) -> tuple[UUID, UUID]:
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketAuthError(code=4401, reason="missing token")

    user_id = _decode_user_id_from_token(token)

    try:
        conversation_uuid = UUID(conversation_id)
    except ValueError as exc:
        raise WebSocketAuthError(code=4400, reason="invalid conversation_id") from exc

    settings = get_settings()
    client_ip = websocket.client.host if websocket.client else "unknown"
    connect_key = f"conn:{user_id}:{client_ip}"
    if not _ws_connect_rate_limiter.allow(connect_key, settings.WS_CONNECT_RATE_LIMIT_PER_MINUTE):
        raise WebSocketAuthError(code=4429, reason="connect rate limited")

    factory = get_session_factory()
    async with factory() as db:
        conv_repo = ConversationRepository(db)
        conv = await conv_repo.get_by_id_for_user(conversation_uuid, user_id)
        if not conv:
            raise WebSocketAuthError(code=4404, reason="conversation not found or unauthorized")

    return user_id, conversation_uuid


async def _authorize_admin_websocket(websocket: WebSocket) -> UUID:
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketAuthError(code=4401, reason="missing token")

    user_id = _decode_user_id_from_token(token)

    settings = get_settings()
    client_ip = websocket.client.host if websocket.client else "unknown"
    connect_key = f"admin:{user_id}:{client_ip}"
    if not _ws_connect_rate_limiter.allow(connect_key, settings.WS_CONNECT_RATE_LIMIT_PER_MINUTE):
        raise WebSocketAuthError(code=4429, reason="connect rate limited")

    factory = get_session_factory()
    async with factory() as db:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise WebSocketAuthError(code=4401, reason="unauthorized")
        if not user.is_admin:
            raise WebSocketAuthError(code=4403, reason="admin required")

    return user_id


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    try:
        user_id, conversation_uuid = await _authorize_websocket_connection(websocket, conversation_id)
    except WebSocketAuthError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

    await websocket.accept()
    connection_key = f"chat:{conversation_id}:{id(websocket)}"
    pool = get_connection_pool()
    await pool.register(
        connection_key,
        websocket,
        groups={
            f"user:{user_id}",
            f"conversation:{conversation_id}",
        },
    )

    logger.info("Chat WS connected conversation=%s user=%s", conversation_id, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type", "")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "close":
                break

            if msg_type != "message":
                await websocket.send_json({"type": "error", "message": "unsupported message type"})
                continue

            settings = get_settings()
            message_limit_key = f"msg:{user_id}:{connection_key}"
            if not _ws_message_rate_limiter.allow(message_limit_key, settings.WS_MESSAGE_RATE_LIMIT_PER_MINUTE):
                await websocket.send_json({
                    "type": "error",
                    "message": "message rate limited",
                })
                await websocket.close(code=4429, reason="message rate limited")
                break

            content = message.get("content", "")
            if not content:
                await websocket.send_json({
                    "type": "error",
                    "message": "message content cannot be empty",
                })
                continue

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
                except Exception as exc:
                    await db.rollback()
                    logger.error("Chat WS message processing failed: %s", exc)
                    await websocket.send_json({
                        "type": "error",
                        "message": str(exc),
                    })
    except WebSocketDisconnect:
        logger.info("Chat WS disconnected conversation=%s user=%s", conversation_id, user_id)
    except Exception as exc:
        logger.error("Chat WS error: %s", exc)
    finally:
        await pool.unregister(connection_key)


@router.websocket("/ws/admin/notifications")
async def websocket_admin_notifications(websocket: WebSocket):
    try:
        user_id = await _authorize_admin_websocket(websocket)
    except WebSocketAuthError as exc:
        await websocket.close(code=exc.code, reason=exc.reason)
        return

    await websocket.accept()
    connection_key = f"admin:{user_id}:{id(websocket)}"
    pool = get_connection_pool()
    await pool.register(
        connection_key,
        websocket,
        groups={
            "admin_notifications",
            f"user:{user_id}",
        },
    )
    await websocket.send_json({"type": "connected", "channel": "admin_notifications"})
    logger.info("Admin WS connected user=%s", user_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data or "{}")
            msg_type = message.get("type")
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "close":
                break
    except WebSocketDisconnect:
        logger.info("Admin WS disconnected user=%s", user_id)
    except Exception as exc:
        logger.error("Admin WS error: %s", exc)
    finally:
        await pool.unregister(connection_key)
