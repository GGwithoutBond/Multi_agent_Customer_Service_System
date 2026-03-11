"""
数据验证工具
"""

import re
from uuid import UUID


def is_valid_uuid(value: str) -> bool:
    """验证是否为有效的 UUID"""
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def is_valid_email(email: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_phone(phone: str) -> bool:
    """验证中国手机号格式"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))


def sanitize_input(text: str, max_length: int = 4096) -> str:
    """清理用户输入"""
    # 去除首尾空白
    text = text.strip()
    # 限制长度
    if len(text) > max_length:
        text = text[:max_length]
    return text
