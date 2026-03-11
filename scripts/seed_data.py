"""
填充示例数据
向数据库中插入测试用的示例数据
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import get_settings
from src.core.security import hash_password
from src.models.user import User
from src.models.user_profile import UserProfile


async def seed_data():
    """填充示例数据"""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # 创建管理员用户
        admin = User(
            username="admin",
            hashed_password=hash_password("admin123"),
            email="admin@example.com",
            display_name="管理员",
            is_admin=True,
        )
        session.add(admin)
        await session.flush()

        # 创建管理员画像
        admin_profile = UserProfile(
            user_id=admin.id,
            preferences={"language": "zh-CN", "theme": "light"},
            tags=["admin"],
        )
        session.add(admin_profile)

        # 创建测试用户
        test_user = User(
            username="testuser",
            hashed_password=hash_password("test123"),
            email="test@example.com",
            display_name="测试用户",
        )
        session.add(test_user)
        await session.flush()

        test_profile = UserProfile(
            user_id=test_user.id,
            preferences={"language": "zh-CN"},
            tags=["test"],
        )
        session.add(test_profile)

        await session.commit()
        print("示例数据已填充!")
        print(f"  管理员: admin / admin123")
        print(f"  测试用户: testuser / test123")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_data())
