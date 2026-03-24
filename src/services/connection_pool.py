"""
Shared WebSocket connection pool.
"""

import asyncio
from collections import defaultdict
from typing import Any, Iterable

from src.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionPool:
    """Tracks websocket connections and group membership."""

    def __init__(self) -> None:
        self._connections: dict[str, Any] = {}
        self._groups: dict[str, set[str]] = defaultdict(set)
        self._connection_groups: dict[str, set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def register(
        self,
        connection_id: str,
        websocket: Any,
        groups: Iterable[str] | None = None,
    ) -> None:
        groups = set(groups or [])
        async with self._lock:
            self._connections[connection_id] = websocket
            self._connection_groups[connection_id] = groups
            for group in groups:
                self._groups[group].add(connection_id)
        logger.info("WS registered connection=%s groups=%s", connection_id, sorted(groups))

    async def unregister(self, connection_id: str) -> None:
        async with self._lock:
            groups = self._connection_groups.pop(connection_id, set())
            for group in groups:
                members = self._groups.get(group)
                if not members:
                    continue
                members.discard(connection_id)
                if not members:
                    self._groups.pop(group, None)
            self._connections.pop(connection_id, None)
        logger.info("WS unregistered connection=%s", connection_id)

    async def send_json(self, connection_id: str, payload: dict) -> bool:
        async with self._lock:
            websocket = self._connections.get(connection_id)
        if websocket is None:
            return False

        try:
            await websocket.send_json(payload)
            return True
        except Exception as exc:
            logger.warning("WS send failed connection=%s error=%s", connection_id, exc)
            await self.unregister(connection_id)
            return False

    async def broadcast_json(self, group: str, payload: dict) -> int:
        async with self._lock:
            target_ids = list(self._groups.get(group, set()))

        if not target_ids:
            return 0

        sent = 0
        for connection_id in target_ids:
            ok = await self.send_json(connection_id, payload)
            if ok:
                sent += 1
        return sent


_pool = ConnectionPool()


def get_connection_pool() -> ConnectionPool:
    return _pool
