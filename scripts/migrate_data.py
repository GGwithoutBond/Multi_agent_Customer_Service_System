"""
数据迁移脚本
用于版本升级时的数据迁移
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def migrate():
    """执行数据迁移"""
    print("数据迁移脚本")
    print("当前版本: v0.1.0")
    print("暂无需要迁移的数据")


if __name__ == "__main__":
    asyncio.run(migrate())
