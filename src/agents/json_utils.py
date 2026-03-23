"""
Agent JSON 解析工具
统一处理 LLM 的 JSON 响应（含 markdown 代码块场景）
"""

from __future__ import annotations

import json
from typing import Any


def extract_json_dict(text: str) -> dict[str, Any] | None:
    """从 LLM 文本中提取 JSON 对象。"""
    if not isinstance(text, str):
        return None

    payload = text.strip()
    if not payload:
        return None

    # 1) 直接解析
    try:
        data = json.loads(payload)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    # 2) 从 markdown 代码块中提取最外层 JSON
    if "```" in payload:
        start = payload.find("{")
        end = payload.rfind("}") + 1
        if start != -1 and end > start:
            try:
                data = json.loads(payload[start:end])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None

    return None
