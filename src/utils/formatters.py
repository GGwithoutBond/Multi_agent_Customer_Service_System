"""
数据格式化工具
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID


def format_datetime(dt: Optional[datetime], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    if dt is None:
        return ""
    return dt.strftime(fmt)


def format_uuid(uid: Optional[UUID]) -> str:
    """格式化 UUID 为短字符串"""
    if uid is None:
        return ""
    return str(uid)[:8]


def format_latency(ms: Optional[int]) -> str:
    """格式化延迟时间"""
    if ms is None:
        return "N/A"
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def format_tokens(count: Optional[int]) -> str:
    """格式化 Token 数"""
    if count is None:
        return "N/A"
    if count < 1000:
        return str(count)
    return f"{count / 1000:.1f}k"
