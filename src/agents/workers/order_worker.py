"""
Order Worker Agent
处理订单查询、物流追踪
支持从工作记忆中提取订单号实体
"""

from typing import Any

from langgraph.prebuilt import create_react_agent

from src.agents.workers.base_worker import BaseWorker
from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import ORDER_WORKER_PROMPT
from src.tools.database_tool import query_order, query_user_orders, process_return

logger = get_logger(__name__)


class OrderWorker(BaseWorker):
    """订单查询 Worker (支持 Tool Calling)"""

    def __init__(self):
        super().__init__(
            name="order_worker",
            description="处理订单查询、物流追踪、订单退货等相关请求，可通过工具自主查询和处理退货",
        )
        self.tools = [query_order, query_user_orders, process_return]
        # Fix 6: 在初始化时创建 Agent 实例（而不是每次请求重建）
        from src.llm import get_llm_client
        chat_model = get_llm_client().get_chat_model()
        self._agent = create_react_agent(chat_model, tools=self.tools)

    async def handle(self, user_input: str, context: dict[str, Any], history: str = "") -> str:
        """使用预建 Agent + 动态 system 消息处理订单请求"""
        try:
            # 如果 context 中传了具体的 order_id，作为补充信息
            order_hint = ""
            if context.get("order_id"):
                order_hint = f"\n[系统提示: 用户当前可能正在关注订单号: {context.get('order_id')}]"

            # 构造动态 prompt（每次根据 persona/history/context 定制）
            _prompt_str = ORDER_WORKER_PROMPT.format(
                persona=self._get_persona(context),
                user_message="请参考用户的最新输入进行处理",
                order_info="请调用 query_order 或 query_user_orders 工具获取订单详细信息及处理进度",
                history=history,
            ) + order_hint

            # Fix 4: 重试时注入上次审查失败原因
            if context.get("is_retry") and context.get("quality_reason"):
                _prompt_str += f"\n\n⚠️ 上次回答存在问题：{context['quality_reason']}，请特别注意改进。"

            logger.info("OrderWorker 开始执行, 用户输入: %s", user_input[:100])
            result = await self._agent.ainvoke({
                "messages": [
                    ("system", _prompt_str),
                    ("user", user_input),
                ]
            })

            messages = result.get("messages", [])
            logger.info("OrderWorker react agent 返回 %d 条消息", len(messages))

            if messages:
                final_content = messages[-1].content
                if final_content:
                    logger.info("OrderWorker 最终回复长度: %d", len(final_content))
                    return final_content
                else:
                    logger.warning("OrderWorker react agent 最后一条消息内容为空")

            return "抱歉，由于系统原因，我现在无法为您查询订单，请稍后再试。"

        except Exception as e:
            logger.error("OrderWorker handle 执行异常: %s", e, exc_info=True)
            return f"抱歉，订单处理过程中遇到了问题: {str(e)[:100]}。请稍后再试或联系人工客服。"
