"""
LangGraph 状态定义
定义工作流中传递的状态结构
"""

from typing import Annotated, Any, Optional, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    Agent 工作流状态

    LangGraph 使用 TypedDict 定义状态，通过 Annotated 的 reducer 函数来决定如何合并状态更新。
    """

    # 消息历史 (使用 add_messages reducer 自动追加)
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # 用户原始输入
    user_input: str

    # 会话 ID
    conversation_id: str

    # 用户 ID
    user_id: Optional[str]

    # 识别的意图
    intent: Optional[str]

    # 路由到的 Worker 类型（支持多 Worker 列表）
    worker_type: Optional[str]

    # 多 Worker 路由列表（并行扇出时使用）
    worker_types: Optional[list[str]]

    # Worker 处理结果
    worker_result: Optional[str]

    # 多 Worker 的结果集（并行扇出时使用）
    worker_results: Optional[dict[str, str]]

    # 上下文信息
    context: dict[str, Any]

    # 最终响应
    response: Optional[str]

    # 错误信息
    error: Optional[str]

    # 是否需要转人工
    needs_human: bool

    # 联网搜索
    web_search: bool

    # 联网搜索结果
    web_search_result: Optional[str]

    # ── 新增：情感与紧急度 ──
    sentiment: Optional[str]  # positive / neutral / negative / angry
    urgency: Optional[str]    # low / medium / high / critical

    # ── 新增：工作记忆快照 ──
    working_memory: Optional[dict[str, Any]]

    # ── 质量审查 ──
    retry_count: int  # 重试次数 (防止死循环, 最多 1 次)
    quality_score: Optional[int]  # 质量打分 1-5
    quality_reason: Optional[str]  # 质量审查失败原因（用于重试时注入改进提示）
    quality_risk_flags: Optional[list[str]]  # 质量风险标签（用于监控与追踪）
