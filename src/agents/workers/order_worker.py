"""
Order Worker Agent
处理订单查询、物流追踪
支持从工作记忆中提取订单号实体
"""

from typing import Any

from langgraph.prebuilt import create_react_agent

from src.agents.workers.base_worker import BaseWorker
from src.core.config import Settings
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
        # 在初始化时创建 Agent 实例（而不是每次请求重建）
        from src.llm import get_llm_client
        chat_model = get_llm_client().get_chat_model()
        self._agent = create_react_agent(chat_model, tools=self.tools)

    async def handle(self, user_input: str, context: dict[str, Any], history: str = "") -> str:
        """使用预建 Agent + 动态 system 消息处理订单请求，支持 MCP 增强"""
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

        # 重试时注入上次审查失败原因
        if context.get("is_retry") and context.get("quality_reason"):
            _prompt_str += f"\n\n⚠️ 上次回答存在问题：{context['quality_reason']}，请特别注意改进。"

        logger.info("OrderWorker 开始执行...")

        # 检查是否启用 MCP 增强模式
        settings = Settings()
        if settings.MCP_ENABLED:
            try:
                result = await self._handle_with_mcp(user_input, _prompt_str, context)
                if result:
                    return result
            except Exception as e:
                logger.warning("OrderWorker MCP 增强模式失败: %s，回退到基础模式", e)

        # ── 降级模式：仅使用默认 tools ──
        result = await self._agent.ainvoke({
            "messages": [
                ("system", _prompt_str),
                ("user", user_input),
            ]
        })

        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return "抱歉，由于系统原因，我现在无法为您处理订单，请稍后再试。"

    async def _handle_with_mcp(
        self, user_input: str, prompt: str, context: dict[str, Any]
    ) -> str | None:
        """
        MCP 增强模式：
        1. 连接淘宝 MCP Server
        2. 加载 MCP 工具 + 本地工具 → 合并交给 Agent
        3. Agent 执行完毕后，提取工具调用结果
        4. 将用户数据同步到数据库
        """
        from src.agents.tools.mcp_client import taobao_mcp_session, extract_tool_results
        from src.services.taobao_sync_service import TaobaoSyncService

        logger.info("OrderWorker 正在连接 MCP...")

        try:
            async with taobao_mcp_session() as (session, mcp_tools):
                logger.info("MCP session 获取成功, tools count: %d", len(mcp_tools) if mcp_tools else 0)

                if not session or not mcp_tools:
                    logger.info("MCP 不可用，跳过增强模式")
                    return None

                # 合并工具列表
                combined_tools = self.tools + mcp_tools
                chat_model = get_llm_client().get_chat_model()
                mcp_agent = create_react_agent(chat_model, tools=combined_tools)

                logger.info(
                    "OrderWorker MCP 增强模式 | 本地工具=%d MCP工具=%d 总工具=%d",
                    len(self.tools), len(mcp_tools), len(combined_tools),
                )

                logger.info("OrderWorker 开始调用 MCP Agent...")

                # 使用 langchain 消息格式
                from langchain_core.messages import HumanMessage
                user_content = f"{prompt}\n\n用户问题: {user_input}"
                messages = [HumanMessage(content=user_content)]

                result = await mcp_agent.ainvoke({"messages": messages})
                logger.info("OrderWorker MCP Agent 调用完成")

                messages = result.get("messages", [])
                if not messages:
                    logger.info("OrderWorker 无返回消息")
                    return None

                # 提取工具调用结果并同步到数据库
                tool_results = extract_tool_results(messages)
                if tool_results:
                    user_id = context.get("user_id")
                    import uuid as uuid_mod
                    uid = None
                    if user_id:
                        try:
                            uid = uuid_mod.UUID(str(user_id))
                        except (ValueError, AttributeError):
                            pass

                    try:
                        await TaobaoSyncService.sync_from_tool_results(
                            tool_results=tool_results,
                            user_id=uid,
                        )
                    except Exception as e:
                        logger.error("OrderWorker 淘宝数据同步异常: %s", e)

                return messages[-1].content
        except Exception as e:
            logger.error("OrderWorker MCP 异常: %s", e)
            return None
