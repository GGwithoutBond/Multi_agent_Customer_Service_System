"""
数据库迁移脚本 — 创建 taobao_user_data 表
用法:  .venv/Scripts/python scripts/migrate_taobao_user_data.py
"""

import asyncio
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.database.postgres import get_engine

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS taobao_user_data (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 关联本系统用户（可选）
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,

    -- 淘宝基本信息
    taobao_nick     VARCHAR(128),
    taobao_avatar   TEXT,

    -- 结构化数据（JSONB）
    addresses       JSONB DEFAULT '[]'::jsonb,
    contacts        JSONB DEFAULT '[]'::jsonb,
    orders          JSONB DEFAULT '[]'::jsonb,
    cart_items       JSONB DEFAULT '[]'::jsonb,
    browsing_history JSONB DEFAULT '[]'::jsonb,
    followed_shops  JSONB DEFAULT '[]'::jsonb,
    wangwang_chats  JSONB DEFAULT '[]'::jsonb,

    -- 原始数据兜底
    raw_data        JSONB DEFAULT '{}'::jsonb,

    -- 最近同步时间
    last_synced_at  TIMESTAMPTZ,

    -- 时间戳
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_taobao_user_data_user_id      ON taobao_user_data(user_id);
CREATE INDEX IF NOT EXISTS idx_taobao_user_data_taobao_nick  ON taobao_user_data(taobao_nick);
"""


async def main():
    print("🚀 开始创建 taobao_user_data 表...")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text(CREATE_TABLE_SQL))
    print("✅ taobao_user_data 表创建成功！")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
