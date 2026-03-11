"""
WebSocket 接口
实时双向通信
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.session import get_session_factory
from src.services.chat_service import ChatService

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])

# 活跃的 WebSocket 连接管理
active_connections: dict[str, WebSocket] = {}


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
    await websocket.accept()
    connection_key = f"{conversation_id}:{id(websocket)}"
    active_connections[connection_key] = websocket

    logger.info("WebSocket 连接建立: %s", conversation_id)

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
                            conversation_id=UUID(conversation_id),
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
        logger.info("WebSocket 连接断开: %s", conversation_id)
    except Exception as e:
        logger.error("WebSocket 异常: %s", e)
    finally:
        active_connections.pop(connection_key, None)
