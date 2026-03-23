from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.api.deps import require_admin_user, require_current_user


@pytest.mark.asyncio
async def test_require_current_user_rejects_missing_authorization():
    with pytest.raises(HTTPException) as exc:
        await require_current_user(authorization=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_admin_user_allows_admin():
    user_id = uuid4()
    db = AsyncMock()
    admin_user = SimpleNamespace(is_active=True, is_admin=True)

    with patch("src.repositories.user_repo.UserRepository.get_by_id", new=AsyncMock(return_value=admin_user)):
        result = await require_admin_user(user_id=user_id, db=db)
    assert result == user_id


@pytest.mark.asyncio
async def test_require_admin_user_rejects_non_admin():
    user_id = uuid4()
    db = AsyncMock()
    normal_user = SimpleNamespace(is_active=True, is_admin=False)

    with patch("src.repositories.user_repo.UserRepository.get_by_id", new=AsyncMock(return_value=normal_user)):
        with pytest.raises(HTTPException) as exc:
            await require_admin_user(user_id=user_id, db=db)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_admin_user_rejects_unknown_user():
    user_id = uuid4()
    db = AsyncMock()

    with patch("src.repositories.user_repo.UserRepository.get_by_id", new=AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as exc:
            await require_admin_user(user_id=user_id, db=db)

    assert exc.value.status_code == 401

