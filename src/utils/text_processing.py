"""
文本处理工具
"""

import re
from typing import Optional


def clean_text(text: str) -> str:
    """清理文本：去除多余空白、特殊字符"""
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """截断文本到指定长度"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def extract_json_from_text(text: str) -> Optional[str]:
    """从文本中提取 JSON 字符串"""
    # 尝试匹配 {} 或 []
    patterns = [
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # 匹配嵌套的 {}
        r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # 匹配嵌套的 []
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group()
    return None


def mask_sensitive_data(text: str) -> str:
    """脱敏处理：隐藏手机号、邮箱、身份证等"""
    # 手机号脱敏
    text = re.sub(r'(1[3-9]\d)\d{4}(\d{4})', r'\1****\2', text)
    # 邮箱脱敏
    text = re.sub(r'(\w{2})\w+(@\w+)', r'\1***\2', text)
    # 身份证脱敏
    text = re.sub(r'(\d{4})\d{10}(\d{4})', r'\1**********\2', text)
    return text
