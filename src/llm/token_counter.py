"""
Token 计数工具
"""

from typing import Optional

import tiktoken

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)

_encoding: Optional[tiktoken.Encoding] = None


def _get_encoding() -> tiktoken.Encoding:
    """获取 tiktoken 编码器 (延迟初始化)"""
    global _encoding
    if _encoding is None:
        try:
            _encoding = tiktoken.encoding_for_model(get_settings().OPENAI_MODEL)
        except KeyError:
            _encoding = tiktoken.get_encoding("cl100k_base")
    return _encoding


def count_tokens(text: str) -> int:
    """计算文本的 Token 数"""
    encoding = _get_encoding()
    return len(encoding.encode(text))


def count_messages_tokens(messages: list[dict]) -> int:
    """
    计算消息列表的 Token 数
    遵循 OpenAI 的消息 Token 计算规则
    """
    encoding = _get_encoding()
    total = 0
    for msg in messages:
        total += 4  # 每条消息固定开销
        for key, value in msg.items():
            total += len(encoding.encode(str(value)))
    total += 2  # 回复起始 Token
    return total


def truncate_text(text: str, max_tokens: int) -> str:
    """截断文本到指定 Token 数"""
    encoding = _get_encoding()
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return encoding.decode(tokens[:max_tokens])
