"""
Product Worker Agent
处理产品咨询、产品推荐
集成淘宝 MCP Server 工具 & 用户数据同步
"""

from typing import Any

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from src.agents.workers.base_worker import BaseWorker
from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import PRODUCT_WORKER_PROMPT

logger = get_logger(__name__)

# 定义给 LLM 用的产品 RAG 检索工具（async 版本，避免事件循环嵌套问题）
@tool
async def search_products(query: str) -> str:
    """
    根据用户的查询内容(query)在产品知识库中检索相关商品信息(如型号、价格、参数)。
    当你需要了解某个产品的具体信息以回答用户时，调用此工具。
    """
    try:
        from src.rag.retriever import HybridRetriever
        retriever = HybridRetriever()
        results = await retriever.retrieve(query, top_k=5)
        if results:
            return "\n\n".join(
                f"[{i+1}] {doc['content']}"
                for i, doc in enumerate(results)
            )
        return "未查找到此产品的相关信息。"
    except Exception as e:
        logger.warning("产品信息检索失败: %s", e)
        return "产品知识库暂不可用，请基于通用知识回答。"



class ProductWorker(BaseWorker):
    """产品咨询 Worker（集成淘宝 MCP 工具 + 用户数据自动同步）"""

    def __init__(self):
        super().__init__(
            name="product_worker",
            description="处理产品咨询、推荐等产品相关请求，可通过工具检索产品库，支持淘宝 MCP 工具",
        )
        self.tools = [search_products]
        # 在初始化时创建基础 Agent 实例（无 MCP 工具的降级版本）
        chat_model = get_llm_client().get_chat_model()
        self._agent = create_react_agent(chat_model, tools=self.tools)

    async def handle(self, user_input: str, context: dict[str, Any], history: str = "") -> str:
        """使用预建 Agent + 动态 system 消息处理产品咨询，支持 MCP 工具 & 数据同步"""
        # 构造额外的提示信息（如果前端穿透了具体的附件商品）
        product_hint = ""
        pd_id = context.get("product_id")
        if pd_id:
            product_hint = f"\n[系统提示: 用户当前可能正在关注商品 {pd_id}]"

        _prompt_str = PRODUCT_WORKER_PROMPT.format(
            persona=self._get_persona(context),
            context="请随时调用 search_products 工具检索产品信息",
            user_message="请参考用户的最新输入进行处理",
            history=history,
        ) + product_hint

        # 重试时注入上次审查失败原因
        if context.get("is_retry") and context.get("quality_reason"):
            _prompt_str += f"\n\n⚠️ 上次回答存在问题：{context['quality_reason']}，请特别注意改进。"

        logger.info("ProductWorker 开始执行...")

        # ── 尝试通过 MCP 增强模式执行（含数据同步）──
        from src.core.config import get_settings
        settings = get_settings()
        if settings.MCP_ENABLED:
            try:
                result = await self._handle_with_mcp(user_input, _prompt_str, context)
                if result:
                    return result
            except Exception as e:
                logger.warning("MCP 增强模式失败: %s，回退到基础模式", e)

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
        return "抱歉，由于系统原因，我现在无法为您查询商品信息。"

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

        async with taobao_mcp_session() as (session, mcp_tools):
            if not session or not mcp_tools:
                logger.info("MCP 不可用，跳过增强模式")
                return None

            # 合并工具列表
            combined_tools = self.tools + mcp_tools
            chat_model = get_llm_client().get_chat_model()
            mcp_agent = create_react_agent(chat_model, tools=combined_tools)

            logger.info(
                "ProductWorker MCP 增强模式 | 本地工具=%d MCP工具=%d 总工具=%d",
                len(self.tools), len(mcp_tools), len(combined_tools),
            )

            result = await mcp_agent.ainvoke({
                "messages": [
                    ("system", prompt),
                    ("user", user_input),
                ]
            })

            messages = result.get("messages", [])
            if not messages:
                return None

            # ── 提取工具调用结果并同步到数据库 ──
            tool_results = extract_tool_results(messages)
            if tool_results:
                user_id = context.get("user_id")
                # 转换 user_id 为 UUID（如果是字符串）
                import uuid as uuid_mod
                uid = None
                if user_id:
                    try:
                        uid = uuid_mod.UUID(str(user_id))
                    except (ValueError, AttributeError):
                        pass

                # 异步同步到数据库（不阻塞返回）
                try:
                    await TaobaoSyncService.sync_from_tool_results(
                        tool_results=tool_results,
                        user_id=uid,
                    )
                except Exception as e:
                    logger.error("淘宝数据同步异常（不影响回复）: %s", e)

            return messages[-1].content
