import asyncio
import os
import sys
import uuid

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.workers.order_worker import OrderWorker
from src.database.session import get_session_factory
from sqlalchemy import select
from src.models.taobao_user_data import TaobaoUserData

async def main():
    worker = OrderWorker()
    user_input = "查看一下当前淘宝用户的信息"
    
    # 模拟一个 context
    user_id = uuid.uuid4()
    context = {"user_id": str(user_id)}
    
    print(f"Executing OrderWorker with input: {user_input}")
    result = await worker.handle(user_input, context)
    print(f"Worker Result: {result}")
    
    # 检查数据库是否同步
    print("Checking database for synchronized data...")
    factory = get_session_factory()
    async with factory() as session:
        # 由于我们没有真实用户，可能按昵称找
        stmt = select(TaobaoUserData).order_by(TaobaoUserData.last_synced_at.desc()).limit(1)
        res = await session.execute(stmt)
        record = res.scalar_one_or_none()
        
        if record:
            print(f"Found synchronized record: {record.taobao_nick} (updated at: {record.last_synced_at})")
        else:
            print("No synchronized record found in database.")

if __name__ == "__main__":
    asyncio.run(main())
