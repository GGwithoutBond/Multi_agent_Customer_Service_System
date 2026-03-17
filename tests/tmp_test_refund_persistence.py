import asyncio
import os
import sys

# Ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.database_tool import query_user_orders, query_order, process_return

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from src.database.session import get_session_factory
from src.models.taobao_user_data import TaobaoUserData
from datetime import datetime, timezone

async def seed_test_orders():
    factory = get_session_factory()
    async with factory() as session:
        # Check if exists
        stmt = select(TaobaoUserData).order_by(TaobaoUserData.last_synced_at.desc())
        result = await session.execute(stmt)
        record = result.scalars().first()
        
        test_orders = [
            {
                "order_id": "ORD-123",
                "product": "Test Product A",
                "status": "已发货",
                "logistics": "SF123",
                "amount": "¥100",
                "order_date": "2024-01-01",
            }
        ]
        
        if not record:
            record = TaobaoUserData(
                taobao_nick="test_user",
                orders=test_orders,
                last_synced_at=datetime.now(timezone.utc)
            )
            session.add(record)
        else:
            record.orders = test_orders
            flag_modified(record, "orders")
            
        await session.commit()
        print("Test data seeded.")

async def test_orders_db():
    await seed_test_orders()

    print("Testing query_user_orders()...")
    orders_str = await query_user_orders.ainvoke({})
    print("User Orders Output:\n", orders_str)

    print("\nTesting query_order('ORD-123')...")
    order_detail = await query_order.ainvoke({"order_id": "ORD-123"})
    print("Order Detail Output:\n", order_detail)
    
    print("\nTesting process_return('ORD-123')...")
    return_result = await process_return.ainvoke({"order_id": "ORD-123"})
    print("Process Return Output:\n", return_result)
    
    print("\nTesting query_order('ORD-123') after return...")
    order_detail_after = await query_order.ainvoke({"order_id": "ORD-123"})
    print("Order Detail Post-Return:\n", order_detail_after)

if __name__ == "__main__":
    asyncio.run(test_orders_db())
