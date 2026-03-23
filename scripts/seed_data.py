"""
填充示例数据
向数据库中插入测试用的示例用户、商品上下文和订单数据
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import get_settings
from src.core.security import hash_password
from src.models.taobao_user_data import TaobaoUserData
from src.models.user import User
from src.models.user_profile import UserProfile


SEEDED_PRODUCTS = [
    {
        "product_id": "P001",
        "name": "iPhone 16 Pro Max",
        "price": 9999,
        "category": "手机",
        "brand": "Apple",
        "specs": "A18 Pro, 256GB, 6.9英寸 OLED, 120Hz",
    },
    {
        "product_id": "P002",
        "name": "iPhone 16",
        "price": 5999,
        "category": "手机",
        "brand": "Apple",
        "specs": "A18, 128GB, 6.1英寸 OLED",
    },
    {
        "product_id": "P005",
        "name": "MacBook Pro 14英寸 M4 Pro",
        "price": 16999,
        "category": "笔记本电脑",
        "brand": "Apple",
        "specs": "M4 Pro, 24GB, 512GB SSD",
    },
    {
        "product_id": "P008",
        "name": "iPad Pro 13英寸 M4",
        "price": 10999,
        "category": "平板电脑",
        "brand": "Apple",
        "specs": "M4, 256GB, Ultra Retina XDR",
    },
    {
        "product_id": "P010",
        "name": "AirPods Pro 2 (USB-C)",
        "price": 1899,
        "category": "耳机",
        "brand": "Apple",
        "specs": "H2 芯片, 主动降噪, 续航 30 小时",
    },
    {
        "product_id": "P012",
        "name": "Sony WH-1000XM5",
        "price": 2499,
        "category": "耳机",
        "brand": "Sony",
        "specs": "头戴降噪, 30 小时续航",
    },
]


SEEDED_ORDERS = [
    {
        "order_id": "ORD-2024001",
        "product_id": "P001",
        "product": "iPhone 16 Pro Max",
        "status": "已发货",
        "logistics": "顺丰速运 SF1234567890",
        "amount": 9999,
        "order_date": "2026-03-10",
        "estimated_delivery": "2026-03-20",
    },
    {
        "order_id": "ORD-2024002",
        "product_id": "P010",
        "product": "AirPods Pro 2 (USB-C)",
        "status": "已签收",
        "logistics": "京东物流 JD9876543210",
        "amount": 1899,
        "order_date": "2026-03-05",
        "estimated_delivery": "2026-03-08",
    },
    {
        "order_id": "ORD-2024003",
        "product_id": "P005",
        "product": "MacBook Pro 14英寸 M4 Pro",
        "status": "处理中",
        "logistics": "暂无",
        "amount": 16999,
        "order_date": "2026-03-18",
        "estimated_delivery": "待发货后更新",
    },
    {
        "order_id": "ORD-2024004",
        "product_id": "P008",
        "product": "iPad Pro 13英寸 M4",
        "status": "待付款",
        "logistics": "暂无",
        "amount": 10999,
        "order_date": "2026-03-19",
        "estimated_delivery": "付款后生成",
    },
    {
        "order_id": "ORD-2024005",
        "product_id": "P012",
        "product": "Sony WH-1000XM5",
        "status": "已签收",
        "return_status": "退货中",
        "logistics": "中通快递 ZTO5566778899",
        "amount": 2499,
        "order_date": "2026-03-01",
        "estimated_delivery": "2026-03-04",
    },
]


def build_cart_items() -> list[dict]:
    return [
        {
            "product_id": item["product_id"],
            "name": item["name"],
            "price": item["price"],
            "category": item["category"],
            "brand": item["brand"],
        }
        for item in SEEDED_PRODUCTS[:4]
    ]


def build_browsing_history() -> list[dict]:
    return [
        {
            "product_id": item["product_id"],
            "name": item["name"],
            "price": item["price"],
            "category": item["category"],
            "brand": item["brand"],
            "viewed_at": f"2026-03-{10 + idx}T10:00:00+08:00",
        }
        for idx, item in enumerate(SEEDED_PRODUCTS)
    ]


async def get_or_create_user(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    email: str,
    display_name: str,
    is_admin: bool = False,
) -> User:
    """按用户名幂等创建用户"""
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user:
        user.email = email
        user.display_name = display_name
        user.is_admin = is_admin
        user.is_active = True
        if password:
            user.hashed_password = hash_password(password)
        return user

    user = User(
        username=username,
        hashed_password=hash_password(password),
        email=email,
        display_name=display_name,
        is_admin=is_admin,
    )
    session.add(user)
    await session.flush()
    return user


async def get_or_create_profile(
    session: AsyncSession,
    *,
    user_id,
    preferences: dict,
    tags: list[str],
) -> UserProfile:
    """按 user_id 幂等创建用户画像"""
    result = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if profile:
        profile.preferences = preferences
        profile.tags = tags
        return profile

    profile = UserProfile(
        user_id=user_id,
        preferences=preferences,
        tags=tags,
    )
    session.add(profile)
    return profile


async def upsert_taobao_context(session: AsyncSession, user: User) -> TaobaoUserData:
    """为测试用户写入订单、购物车和浏览商品数据"""
    result = await session.execute(select(TaobaoUserData).where(TaobaoUserData.user_id == user.id))
    record = result.scalar_one_or_none()

    payload = {
        "orders": SEEDED_ORDERS,
        "cart_items": build_cart_items(),
        "browsing_history": build_browsing_history(),
        "raw_data": {
            "seed_source": "scripts.seed_data",
            "orders": SEEDED_ORDERS,
            "cart_items": build_cart_items(),
            "browsing_history": build_browsing_history(),
        },
        "last_synced_at": datetime.now(timezone.utc),
        "taobao_nick": "testuser_tb",
    }

    if record:
        record.taobao_nick = payload["taobao_nick"]
        record.orders = payload["orders"]
        record.cart_items = payload["cart_items"]
        record.browsing_history = payload["browsing_history"]
        record.raw_data = payload["raw_data"]
        record.last_synced_at = payload["last_synced_at"]
        return record

    record = TaobaoUserData(
        user_id=user.id,
        taobao_nick=payload["taobao_nick"],
        orders=payload["orders"],
        cart_items=payload["cart_items"],
        browsing_history=payload["browsing_history"],
        raw_data=payload["raw_data"],
        last_synced_at=payload["last_synced_at"],
    )
    session.add(record)
    return record


async def seed_data():
    """填充示例数据"""
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        admin = await get_or_create_user(
            session,
            username="admin",
            password="admin123",
            email="admin@example.com",
            display_name="管理员",
            is_admin=True,
        )
        await get_or_create_profile(
            session,
            user_id=admin.id,
            preferences={"language": "zh-CN", "theme": "light"},
            tags=["admin"],
        )

        test_user = await get_or_create_user(
            session,
            username="testuser",
            password="test123",
            email="test@example.com",
            display_name="测试用户",
        )
        await get_or_create_profile(
            session,
            user_id=test_user.id,
            preferences={"language": "zh-CN"},
            tags=["test"],
        )

        await upsert_taobao_context(session, test_user)

        await session.commit()
        print("示例数据已填充或更新!")
        print("  管理员: admin / admin123")
        print("  测试用户: testuser / test123")
        print(f"  已写入商品上下文: {len(SEEDED_PRODUCTS)} 条")
        print(f"  已写入订单数据: {len(SEEDED_ORDERS)} 条")
        print("  订单状态覆盖: 已发货 / 已签收 / 处理中 / 待付款 / 退货中")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_data())
