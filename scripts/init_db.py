"""
初始化数据库
创建所有表并插入初始数据
"""

import asyncio
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config import get_settings
from src.models import Base


async def init_database():
    """初始化数据库 - 创建所有表"""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    print(f"正在连接数据库: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")

    async with engine.begin() as conn:
        print("正在创建数据库表...")
        await conn.run_sync(Base.metadata.create_all)
        print("数据库表创建完成!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())
