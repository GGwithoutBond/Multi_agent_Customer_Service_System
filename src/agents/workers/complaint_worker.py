"""
Complaint Worker Agent
处理投诉反馈，自动创建工单（Tool Calling）
支持情感感知、自动升级和真实工单追踪
"""

from typing import Any

from langgraph.prebuilt import create_react_agent

from src.agents.workers.base_worker import BaseWorker
from src.agents.tools.database_tool import create_ticket
from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import COMPLAINT_WORKER_PROMPT

logger = get_logger(__name__)


class ComplaintWorker(BaseWorker):
    """投诉处理 Worker（支持 Tool Calling 自动创建工单）"""

    def __init__(self):
        super().__init__(
            name="complaint_worker",
            description="处理用户投诉、自动创建工单，支持情感感知和自动升级",
        )
        self.tools = [create_ticket]

    async def handle(self, user_input: str, context: dict[str, Any], history: str = "") -> str:
        """使用 React Agent + create_ticket 工具处理投诉"""
        try:
            sentiment = context.get("sentiment", "neutral")
            urgency = context.get("urgency", "medium")
            conversation_id = context.get("conversation_id", "")
            user_id = context.get("user_id", "")

            llm_client = get_llm_client()
            chat_model = llm_client.get_chat_model()

            # 构建 Prompt：注入情感、紧急度、会话上下文
            _prompt_str = COMPLAINT_WORKER_PROMPT.format(
                persona=self._get_persona(context),
                user_message="请参考用户的最新输入进行处理",
                history=history,
            )

            # 如果用户情绪激动，强化安抚指令
            if sentiment in ("angry", "frustrated") or urgency in ("high", "critical"):
                _prompt_str += (
                    f"\n\n⚠️ 特别注意：用户情绪较为激动（情感: {sentiment}，紧急度: {urgency}）。"
                    "请先真诚安抚情绪，再提供解决方案，语气要格外温和。"
                    "主动提出创建投诉工单（调用 create_ticket 工具），让用户感受到问题被认真对待。"
                )

            # 注入系统上下文供工具使用（通过 system 消息提示 Agent）
            system_hint = (
                f"[系统上下文] conversation_id={conversation_id or 'unknown'}, "
                f"user_id={user_id or 'unknown'}, "
                f"urgency={urgency}, sentiment={sentiment}. "
                "调用 create_ticket 时请使用这些值填充对应参数。"
            )
            _prompt_str += f"\n\n{system_hint}"

            agent = create_react_agent(chat_model, tools=self.tools, prompt=_prompt_str)

            logger.info("ComplaintWorker React Agent 开始处理: %s", user_input[:100])
            result = await agent.ainvoke({
                "messages": [("user", user_input)]
            })

            messages = result.get("messages", [])
            if messages:
                final_content = messages[-1].content
                if final_content:
                    logger.info("ComplaintWorker 最终回复长度: %d", len(final_content))
                    return final_content

            return "非常抱歉您遇到了问题，请稍后再试或直接联系人工客服。"

        except Exception as e:
            logger.error("ComplaintWorker handle 执行异常: %s", e, exc_info=True)
            return (
                "非常抱歉给您带来了不好的体验。"
                f"由于系统原因，工单创建暂时失败，请稍后重试或联系人工客服。（错误: {str(e)[:60]}）"
            )
