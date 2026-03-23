import io
import os
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

os.environ["DEBUG"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests"

from src.api.rate_limit import SlidingWindowRateLimiter
from src.api.v1 import upload as upload_module
from src.api.v1 import websocket as websocket_module


class _FakeSessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _build_fake_factory(session):
    def _factory():
        return _FakeSessionContext(session)

    return _factory


@pytest.mark.asyncio
async def test_upload_rate_limit_blocks_frequent_requests(tmp_path):
    upload_module._upload_rate_limiter = SlidingWindowRateLimiter(window_seconds=60)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    user_id = uuid4()
    settings = SimpleNamespace(
        UPLOAD_RATE_LIMIT_PER_MINUTE=1,
        BASE_DIR=str(tmp_path),
    )

    with patch("src.api.v1.upload.get_settings", return_value=settings):
        file1 = UploadFile(filename="a.txt", file=io.BytesIO(b"hello"), headers={"content-type": "text/plain"})
        result = await upload_module.upload_file(request=request, file=file1, user_id=user_id)
        assert result["name"] == "a.txt"

        file2 = UploadFile(filename="b.txt", file=io.BytesIO(b"world"), headers={"content-type": "text/plain"})
        with pytest.raises(HTTPException) as exc:
            await upload_module.upload_file(request=request, file=file2, user_id=user_id)
        assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_websocket_authorize_rejects_missing_token():
    websocket = SimpleNamespace(query_params={}, client=SimpleNamespace(host="127.0.0.1"))
    with pytest.raises(websocket_module.WebSocketAuthError) as exc:
        await websocket_module._authorize_websocket_connection(websocket, str(uuid4()))
    assert exc.value.code == 4401


@pytest.mark.asyncio
async def test_websocket_authorize_rejects_non_owner():
    websocket_module._ws_connect_rate_limiter = SlidingWindowRateLimiter(window_seconds=60)
    user_id = uuid4()
    conversation_id = uuid4()
    websocket = SimpleNamespace(query_params={"token": "valid-token"}, client=SimpleNamespace(host="127.0.0.1"))
    db_session = AsyncMock()
    settings = SimpleNamespace(WS_CONNECT_RATE_LIMIT_PER_MINUTE=20)

    with patch("src.api.v1.websocket.decode_access_token", return_value={"sub": str(user_id)}), \
            patch("src.api.v1.websocket.get_session_factory", return_value=_build_fake_factory(db_session)), \
            patch("src.repositories.conversation_repo.ConversationRepository.get_by_id_for_user", new=AsyncMock(return_value=None)), \
            patch("src.api.v1.websocket.get_settings", return_value=settings):
        with pytest.raises(websocket_module.WebSocketAuthError) as exc:
            await websocket_module._authorize_websocket_connection(websocket, str(conversation_id))

    assert exc.value.code == 4404


@pytest.mark.asyncio
async def test_websocket_authorize_rate_limit():
    websocket_module._ws_connect_rate_limiter = SlidingWindowRateLimiter(window_seconds=60)
    user_id = uuid4()
    conversation_id = uuid4()
    websocket = SimpleNamespace(query_params={"token": "valid-token"}, client=SimpleNamespace(host="127.0.0.1"))
    db_session = AsyncMock()
    settings = SimpleNamespace(WS_CONNECT_RATE_LIMIT_PER_MINUTE=1)
    conv = SimpleNamespace(id=conversation_id, user_id=user_id)

    with patch("src.api.v1.websocket.decode_access_token", return_value={"sub": str(user_id)}), \
            patch("src.api.v1.websocket.get_session_factory", return_value=_build_fake_factory(db_session)), \
            patch("src.repositories.conversation_repo.ConversationRepository.get_by_id_for_user", new=AsyncMock(return_value=conv)), \
            patch("src.api.v1.websocket.get_settings", return_value=settings):
        first_user_id, first_conv_id = await websocket_module._authorize_websocket_connection(websocket, str(conversation_id))
        assert first_user_id == user_id
        assert first_conv_id == conversation_id

        with pytest.raises(websocket_module.WebSocketAuthError) as exc:
            await websocket_module._authorize_websocket_connection(websocket, str(conversation_id))

    assert exc.value.code == 4429
