"""
聊天服务
核心业务逻辑 - 协调 Agent 工作流处理用户消息
优化: 真正逐 Token 流式输出、用户画像自动更新、可观测性日志
"""

import asyncio
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, List, Optional
from uuid import UUID

from langchain_core.messages import HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.graph.nodes import _orchestrator
from src.agents.graph.workflow import get_workflow
from src.agents.quality_agent import QualityAgent
from src.agents.summary_agent import SummaryAgent
from src.core.config import get_settings
from src.core.exceptions import AgentError
from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import ORCHESTRATOR_AGGREGATE_PROMPT, DEFAULT_PERSONA, PERSONA_TEMPLATES
from src.llm.token_counter import count_tokens
from src.memory.memory_manager import MemoryManager
from src.models.conversation import Conversation, ConversationChannel, ConversationStatus
from src.models.message import Message, MessageRole
from src.repositories.conversation_repo import ConversationRepository
from src.repositories.message_repo import MessageRepository
from src.schemas.chat import ChatResponse, ChatStreamChunk
from src.services.semantic_cache import SemanticCache
from src.database.session import get_session_factory
from sqlalchemy import select
from src.models.taobao_user_data import TaobaoUserData

logger = get_logger(__name__)


class ChatService:
    """聊天服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)
        self.memory_manager = MemoryManager(db_session=db)
        self.semantic_cache = SemanticCache()
        self.summary_agent = SummaryAgent()

    @staticmethod
    def _next_message_ts(last_ts: Optional[datetime]) -> datetime:
        """Return a strictly monotonic UTC timestamp for message writes."""
        now = datetime.now(timezone.utc)
        if last_ts is None:
            return now
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)
        min_next = last_ts + timedelta(microseconds=1)
        return now if now > min_next else min_next

    async def process_message(
        self,
        message: str,
        conversation_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        context: Optional[dict] = None,
        attachments: Optional[List[dict]] = None,
        web_search: bool = False,
    ) -> ChatResponse:
        """
        处理用户消息（同步模式）
        """
        start_time = time.time()
        last_message_ts: Optional[datetime] = None

        # 1. 获取或创建会话
        conversation = await self._get_or_create_conversation(
            conversation_id, user_id
        )

        # 2. 保存用户消息（含附件元信息）
        msg_metadata = {}
        if attachments:
            msg_metadata["attachments"] = attachments
        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=message,
            metadata_=msg_metadata if msg_metadata else None,
            created_at=self._next_message_ts(last_message_ts),
        )
        last_message_ts = user_msg.created_at
        user_msg = await self.msg_repo.create(user_msg)

        try:
            # 3. 加载对话上下文
            history_messages = await self.memory_manager.load_context(
                conversation_id=str(conversation.id),
                user_id=str(user_id) if user_id else None,
            )

            # 4. 尝试命中语义缓存
            response_text = None
            intent = "cache_hit"
            worker_type = "cache"
            detected_sentiment = None
            detected_urgency = None
            settings = get_settings()
            if not attachments and settings.ENABLE_SEMANTIC_CACHE:
                cached_res = await self.semantic_cache.get(message)
                if cached_res:
                    response_text = cached_res

            # 5. 执行 LangGraph 工作流
            if not response_text:
                workflow = get_workflow()
                initial_state = self._build_initial_state(
                    message, conversation.id, user_id, history_messages, context, web_search, attachments
                )

                result = await workflow.ainvoke(initial_state)
                
                # 手动调用 aggregation 因为它已被移出 Graph 实现真正流式支持
                if not result.get("response"):
                    agg_res = await _orchestrator.aggregate_response(result)
                    result["response"] = agg_res["response"]

                response_text = result.get("response", "抱歉，我暂时无法回答您的问题。")
                intent = result.get("intent")
                worker_type = result.get("worker_type")
                detected_sentiment = result.get("sentiment")
                detected_urgency = result.get("urgency")
                
                # 写入缓存
                if not attachments and settings.ENABLE_SEMANTIC_CACHE and result.get("quality_score", 5) >= 3:
                     await self.semantic_cache.set(message, response_text)

            # 6. 计算指标（优化 6.4: 可观测性）
            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = count_tokens(message) + count_tokens(response_text)

            self._log_metrics(
                intent=intent,
                worker_type=worker_type,
                sentiment=detected_sentiment,
                urgency=detected_urgency,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
            )

            # 6. 保存 AI 回复
            ai_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=response_text,
                intent=intent,
                worker_type=worker_type,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                created_at=self._next_message_ts(last_message_ts),
            )
            last_message_ts = ai_msg.created_at
            ai_msg = await self.msg_repo.create(ai_msg)

            # 7. 更新记忆（含用户画像自动提取）
            await self.memory_manager.save_turn(
                conversation_id=str(conversation.id),
                user_message=message,
                assistant_message=response_text,
                user_id=str(user_id) if user_id else None,
            )

            # 8. 更新会话标题（首次对话）
            if not conversation.title:
                title = message[:50] + ("..." if len(message) > 50 else "")
                await self.conv_repo.update_by_id(conversation.id, title=title)

            return ChatResponse(
                conversation_id=conversation.id,
                message_id=ai_msg.id,
                content=response_text,
                intent=intent,
                worker_type=worker_type,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error("消息处理失败: %s", e, exc_info=True)
            error_text = "抱歉，处理您的消息时出现了问题。请稍后再试。"
            error_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=error_text,
                latency_ms=int((time.time() - start_time) * 1000),
                created_at=self._next_message_ts(last_message_ts),
            )
            await self.msg_repo.create(error_msg)
            raise AgentError(f"消息处理失败: {e}")

    async def process_message_stream(
        self,
        message: str,
        conversation_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        context: Optional[dict] = None,
        attachments: Optional[List[dict]] = None,
        web_search: bool = False,
    ) -> AsyncIterator[ChatStreamChunk]:
        """
        处理用户消息（流式模式）

        优化 2.1: 使用 LLM streaming 在 response_generator 阶段逐 token 输出
        """
        start_time = time.time()
        last_message_ts: Optional[datetime] = None

        # 获取或创建会话
        conversation = await self._get_or_create_conversation(
            conversation_id, user_id
        )

        # 首包固定发送 meta，前端据此绑定 conversation_id
        yield ChatStreamChunk(type="meta", conversation_id=conversation.id)

        # 保存用户消息（含附件元信息）
        msg_metadata = {}
        if attachments:
            msg_metadata["attachments"] = attachments
        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=message,
            metadata_=msg_metadata if msg_metadata else None,
            created_at=self._next_message_ts(last_message_ts),
        )
        last_message_ts = user_msg.created_at
        await self.msg_repo.create(user_msg)

        try:
            # 加载上下文
            history_messages = await self.memory_manager.load_context(
                conversation_id=str(conversation.id),
                user_id=str(user_id) if user_id else None,
            )

            # 尝试命中语义缓存
            settings = get_settings()
            if not attachments and settings.ENABLE_SEMANTIC_CACHE:
                cached_res = await self.semantic_cache.get(message)
                if cached_res:
                    yield ChatStreamChunk(
                        type="thinking",
                        step="⚡ 从语义缓存返回",
                        content="命中缓存...",
                    )
                    chunk_size = 4
                    for i in range(0, len(cached_res), chunk_size):
                        chunk = cached_res[i:i + chunk_size]
                        yield ChatStreamChunk(type="chunk", content=chunk)
                    
                    # 保存缓存回复
                    ai_msg = Message(
                        conversation_id=conversation.id,
                        role=MessageRole.ASSISTANT,
                        content=cached_res,
                        intent="cache_hit",
                        worker_type="cache",
                        tokens_used=count_tokens(message) + count_tokens(cached_res),
                        latency_ms=int((time.time() - start_time) * 1000),
                        created_at=self._next_message_ts(last_message_ts),
                    )
                    last_message_ts = ai_msg.created_at
                    ai_msg = await self.msg_repo.create(ai_msg)
                    yield ChatStreamChunk(type="done", message_id=ai_msg.id)
                    if settings.ENABLE_ASYNC_POSTPROCESS:
                        asyncio.create_task(
                            self._run_stream_postprocess(
                                conversation_id=conversation.id,
                                user_message=message,
                                assistant_message=cached_res,
                                user_id=user_id,
                            )
                        )
                    else:
                        await self._run_stream_postprocess(
                            conversation_id=conversation.id,
                            user_message=message,
                            assistant_message=cached_res,
                            user_id=user_id,
                        )
                    return

            # 执行工作流
            workflow = get_workflow()
            initial_state = self._build_initial_state(
                message, conversation.id, user_id, history_messages, context, web_search, attachments
            )

            # Worker 节点到步骤描述的映射
            worker_step_map = {
                "product_worker": "🔍 正在搜索商品知识库...",
                "order_worker": "📦 正在查询订单信息...",
                "faq_worker": "📚 正在检索常见问题...",
                "complaint_worker": "📝 正在处理投诉信息...",
                "human_worker": "🙋 正在转接人工客服...",
            }

            # ── 优化 2.1: 使用 astream 获取中间节点输出 ──
            full_response = ""
            worker_result_for_stream = ""
            web_search_result_for_stream = ""
            detected_intent = ""
            detected_worker_type = ""
            detected_sentiment = ""
            detected_urgency = ""
            
            ai_action_buttons = []

            async for event in workflow.astream(initial_state):
                for node_name, node_output in event.items():
                    if node_name == "orchestrator":
                        detected_intent = node_output.get("intent", "")
                        detected_worker_type = node_output.get("worker_type", "")
                        detected_sentiment = node_output.get("sentiment", "")
                        detected_urgency = node_output.get("urgency", "")
                        yield ChatStreamChunk(
                            type="thinking",
                            step="🤔 正在分析您的意图...",
                            content=f"识别到意图: {detected_intent}" if detected_intent else "正在思考...",
                        )

                    elif node_name in worker_step_map:
                        worker_result_for_stream = node_output.get("worker_result", "")
                        yield ChatStreamChunk(
                            type="tool_call",
                            step=worker_step_map[node_name],
                            content="",
                        )

                    elif node_name == "web_search":
                        web_search_result_for_stream = node_output.get("web_search_result", "")
                        yield ChatStreamChunk(
                            type="tool_call",
                            step="🌐 正在联网搜索...",
                            content=web_search_result_for_stream[:200] if web_search_result_for_stream else "",
                        )

            # ── 优化 2.1: 真正的逐 token 流式输出 ──
            # 在 LangGraph 结束后，开始根据条件推流合并结果
            if not worker_result_for_stream and not web_search_result_for_stream:
                # 尝试提供更友好的回复而不是通用错误
                logger.warning("worker_result 和 web_search_result 都为空, intent=%s, worker=%s",
                               detected_intent, detected_worker_type)
                full_response = "抱歉，处理过程中遇到了问题。请您再描述一下您的需求，我会重新为您处理。"
                yield ChatStreamChunk(type="chunk", content=full_response)
            
            elif not web_search_result_for_stream and worker_result_for_stream:
                # 没有任何联网搜索，直接把 worker 结果块发送
                full_response = worker_result_for_stream
                chunk_size = 4  # 每次发送 4 个字符以模拟平滑
                for i in range(0, len(full_response), chunk_size):
                    chunk = full_response[i:i + chunk_size]
                    yield ChatStreamChunk(type="chunk", content=chunk)

                # ── 退货流程交互按钮注入 ──
                # 检查是否是退货相关的回复，注入交互式按钮
                if detected_worker_type == "order_worker":
                    await self._emit_return_order_actions(full_response, message)

                    # 用 generator 方式发送 action_buttons
                    action_chunks = await self._build_return_order_action_chunks(full_response, message)
                    for ac in action_chunks:
                        if ac.type == "action_buttons" and hasattr(ac, "actions"):
                            ai_action_buttons.extend(ac.actions)
                        yield ac
            
            else:
                persona_style = context.get("persona_style") if context else None
                current_persona = PERSONA_TEMPLATES.get(persona_style, DEFAULT_PERSONA) if persona_style else DEFAULT_PERSONA

                llm_client = get_llm_client()
                base_prompt = ORCHESTRATOR_AGGREGATE_PROMPT.format(
                    persona=current_persona,
                    user_message=message,
                    worker_type=detected_worker_type,
                    worker_result=worker_result_for_stream,
                )
                if web_search_result_for_stream:
                    base_prompt += (
                        f"\n\n## 联网搜索结果（最新互联网信息）\n{web_search_result_for_stream}\n\n"
                        "请结合以上搜索结果和知识库信息，为用户提供全面且准确的回答。"
                        "如果引用了搜索结果，请标注来源。"
                    )
                
                async for chunk in llm_client.stream([HumanMessage(content=base_prompt)]):
                    full_response += chunk
                    yield ChatStreamChunk(type="chunk", content=chunk)

            # 写入缓存
            if not attachments and settings.ENABLE_SEMANTIC_CACHE and full_response and not full_response.startswith("抱歉"):
                 await self.semantic_cache.set(message, full_response)

            # 保存完整回复
            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = count_tokens(message) + count_tokens(full_response)

            # 可观测性日志
            self._log_metrics(
                intent=detected_intent,
                worker_type=detected_worker_type,
                sentiment=detected_sentiment,
                urgency=detected_urgency,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
            )

            ai_msg_metadata = {}
            if ai_action_buttons:
                ai_msg_metadata["action_buttons"] = ai_action_buttons

            ai_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=full_response or "抱歉，我暂时无法回答您的问题。",
                intent=detected_intent or None,
                worker_type=detected_worker_type or None,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                metadata_=ai_msg_metadata if ai_msg_metadata else None,
                created_at=self._next_message_ts(last_message_ts),
            )
            last_message_ts = ai_msg.created_at
            ai_msg = await self.msg_repo.create(ai_msg)

            # 生成会话标题（首轮对话）并随 done 事件返回给前端
            generated_title: Optional[str] = None
            if not conversation.title:
                try:
                    await self._finalize_first_turn_summary(
                        conversation=conversation,
                        user_message=message,
                        assistant_message=full_response,
                    )
                    # 读取刚写入的标题
                    updated_conv = await self.conv_repo.get_by_id(conversation.id)
                    generated_title = getattr(updated_conv, "title", None) or None
                except Exception as title_exc:
                    logger.warning("标题生成失败（不影响主流程）: %s", title_exc)

            review_state = {
                "intent": detected_intent,
                "worker_type": detected_worker_type,
                "sentiment": detected_sentiment,
                "urgency": detected_urgency,
                "conversation_id": str(conversation.id),
                "user_input": message,
                "worker_result": full_response,
            }
            if QualityAgent.should_run_sync_review(review_state):
                await self._run_async_quality_review(review_state)
            elif QualityAgent.should_run_async_review(review_state):
                asyncio.create_task(self._run_async_quality_review(review_state))

            yield ChatStreamChunk(type="done", message_id=ai_msg.id, title=generated_title)
            if settings.ENABLE_ASYNC_POSTPROCESS:
                asyncio.create_task(
                    self._run_stream_postprocess(
                        conversation_id=conversation.id,
                        user_message=message,
                        assistant_message=full_response,
                        user_id=user_id,
                    )
                )
            else:
                await self._run_stream_postprocess(
                    conversation_id=conversation.id,
                    user_message=message,
                    assistant_message=full_response,
                    user_id=user_id,
                )

        except Exception as e:
            logger.error("流式消息处理失败: %s", e)
            yield ChatStreamChunk(type="error", error=str(e))

    async def handle_feedback(
        self,
        message_id: UUID,
        rating: int,
        conversation_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Optional[str]:
        """
        优化 2.4: 处理用户反馈闭环
        负面反馈（rating <= 2）时自动触发重新回答
        """
        if rating <= 2 and conversation_id:
            logger.info("📉 负面反馈 (rating=%d)，尝试重新回答", rating)

            # 获取原始消息
            original_msg = await self.msg_repo.get_by_id(message_id)
            if original_msg:
                # 获取对应的用户消息（前一条）
                messages = await self.msg_repo.get_by_conversation(
                    conversation_id, limit=10
                )
                user_message = None
                for i, msg in enumerate(messages):
                    if msg.id == message_id and i > 0:
                        user_message = messages[i - 1].content
                        break

                if user_message:
                    # 通知前端正在重新回答
                    return "正在为您重新生成回答..."
        return None

    def _build_initial_state(
        self,
        message: str,
        conversation_id: UUID,
        user_id: Optional[UUID],
        history_messages: list,
        context: Optional[dict],
        web_search: bool,
        attachments: Optional[List[dict]] = None,
    ) -> dict:
        """构建 LangGraph 工作流的初始状态，注入附件上下文"""
        enriched_context = dict(context or {})
        enriched_input = message

        # ── 关键修复: 将附件信息注入到 user_input 和 context 中 ──
        if attachments:
            enriched_context["attachments"] = attachments
            attachment_descriptions = []

            for att in attachments:
                att_type = att.get("type", "")
                if att_type == "product":
                    name = att.get("name", "")
                    product_id = att.get("product_id", "")
                    price = att.get("price", "")
                    desc = f"[用户选择了商品: {name} (编号:{product_id}, 价格:¥{price})]"
                    attachment_descriptions.append(desc)
                    enriched_context["selected_product"] = att
                elif att_type == "order":
                    order_id = att.get("order_id", "")
                    name = att.get("name", "")
                    status = att.get("status", "")
                    desc = f"[用户选择了订单: {order_id} - {name} (状态:{status})]"
                    attachment_descriptions.append(desc)
                    enriched_context["selected_order"] = att
                    enriched_context["order_id"] = order_id
                elif att_type == "image":
                    name = att.get("name", "图片")
                    attachment_descriptions.append(f"[用户上传了图片: {name}]")
                elif att_type == "file":
                    name = att.get("name", "文件")
                    attachment_descriptions.append(f"[用户上传了文件: {name}]")

            if attachment_descriptions:
                context_prefix = "\n".join(attachment_descriptions)
                enriched_input = f"{context_prefix}\n{message}" if message else context_prefix

        return {
            "messages": history_messages + [HumanMessage(content=enriched_input)],
            "user_input": enriched_input,
            "conversation_id": str(conversation_id),
            "user_id": str(user_id) if user_id else None,
            "intent": None,
            "worker_type": None,
            "worker_types": None,
            "worker_result": None,
            "worker_results": None,
            "context": enriched_context,
            "response": None,
            "error": None,
            "needs_human": False,
            "web_search": web_search,
            "web_search_result": None,
            "sentiment": None,
            "urgency": None,
            "working_memory": None,
        }

    async def _run_stream_postprocess(
        self,
        conversation_id: UUID,
        user_message: str,
        assistant_message: str,
        user_id: Optional[UUID],
    ) -> None:
        """流式 done 后置处理：写入记忆，避免阻塞首屏响应。"""
        try:
            await self.memory_manager.save_turn(
                conversation_id=str(conversation_id),
                user_message=user_message,
                assistant_message=assistant_message,
                user_id=str(user_id) if user_id else None,
            )
        except Exception as exc:
            logger.warning("流式后处理失败: %s", exc)

    async def _run_async_quality_review(self, state: dict[str, Any]) -> None:
        """执行质量审查（同步或异步调度均复用该协程）。"""
        try:
            agent = QualityAgent()
            await agent.process(state)
        except Exception as exc:
            logger.warning("异步质量审查失败: %s", exc)

    async def _finalize_first_turn_summary(
        self,
        conversation: Conversation,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """
        首轮完成后生成标题/摘要。
        仅在会话消息数为 2（用户+助手各一条）时执行，避免后续轮次覆盖上下文。
        """
        try:
            msg_count = await self.msg_repo.count_by_conversation(conversation.id)
            if msg_count != 2:
                return

            latest_conv = await self.conv_repo.get_by_id(conversation.id)
            if not latest_conv:
                return

            summary_payload = await self.summary_agent.process(
                {
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                }
            )

            update_data: dict[str, Any] = {}
            proposed_title = str(summary_payload.get("title") or "").strip()
            if not getattr(latest_conv, "title", None) and proposed_title:
                update_data["title"] = proposed_title

            summary_text = str(summary_payload.get("summary") or "").strip()
            if summary_text:
                update_data["summary"] = summary_text

            key_points = summary_payload.get("key_points") or []
            if key_points:
                metadata = dict(getattr(latest_conv, "metadata_", None) or {})
                metadata["summary_key_points"] = key_points
                update_data["metadata_"] = metadata

            if update_data:
                await self.conv_repo.update_by_id(conversation.id, **update_data)
        except Exception as exc:
            logger.warning("首轮摘要生成失败: %s", exc)

    @staticmethod
    def _log_metrics(
        intent: Optional[str] = None,
        worker_type: Optional[str] = None,
        sentiment: Optional[str] = None,
        urgency: Optional[str] = None,
        latency_ms: int = 0,
        tokens_used: int = 0,
    ) -> None:
        """优化 6.4: 可观测性日志"""
        logger.info(
            "📊 请求指标 | intent=%s worker=%s sentiment=%s urgency=%s "
            "latency=%dms tokens=%d",
            intent or "-",
            worker_type or "-",
            sentiment or "-",
            urgency or "-",
            latency_ms,
            tokens_used,
        )

    async def _emit_return_order_actions(self, response: str, user_message: str):
        """日志辅助：记录退货流程检测情况"""
        is_return_flow = self._is_return_order_flow(response, user_message)
        if is_return_flow:
            logger.info("🔄 检测到退货流程，将注入交互按钮")

    @staticmethod
    def _is_return_order_flow(response: str, user_message: str) -> bool:
        """检测是否是退货流程（排除已确认/已完成的情况）"""
        # 用户已经确认或取消 → 不再注入按钮
        skip_phrases = ["确认退货", "取消退货", "确认", "取消"]
        if any(user_message.strip().startswith(sp) for sp in skip_phrases):
            return False
        # 回复中已经显示退货完成 → 不再注入按钮
        done_phrases = ["已成功提交", "退货审核中", "退货申请已", "已经申请过", "退货中", "退货已完成", "已更新为"]
        if any(dp in response for dp in done_phrases):
            return False
        return_keywords = ["退货", "退款", "退回", "退换"]
        has_return_intent = any(kw in user_message for kw in return_keywords)
        has_order_list = "ORD-" in response or "订单" in response
        return has_return_intent and has_order_list

    async def _build_return_order_action_chunks(self, response: str, user_message: str) -> list:
        """
        检测退货流程并构建 action_buttons SSE 块
        返回 ChatStreamChunk 列表
        """
        if not self._is_return_order_flow(response, user_message):
            return []

        chunks = []

        # 检查回复中是否包含订单列表（用户未选择具体订单）
        order_ids_in_response = re.findall(r'ORD-\d+', response)
        order_ids_in_response = list(set(order_ids_in_response))  # 去重

        if not order_ids_in_response:
             return []

        # 获取实际数据库中的订单以回显卡片数据
        factory = get_session_factory()
        async with factory() as session:
             stmt = select(TaobaoUserData).order_by(TaobaoUserData.last_synced_at.desc())
             result = await session.execute(stmt)
             taobao_user = result.scalars().first()
             orders = taobao_user.orders if taobao_user and isinstance(taobao_user.orders, list) else []

        if len(order_ids_in_response) > 1:
            # 用户还未选择具体订单 → 提供订单选择卡片
            order_cards = []
            for oid in order_ids_in_response:
                # 寻找匹配的订单数据
                order_data = next((o for o in orders if str(o.get("order_id", "")).upper() == oid.upper()), None)
                if order_data:
                    order_cards.append({
                        "type": "order_card",
                        "order_id": oid,
                        "product": order_data.get("product", oid),
                        "status": order_data.get("status", "未知状态"),
                        "amount": order_data.get("amount", ""),
                        "label": f"退货: {order_data.get('product', oid)}",
                        "action": f"我要退货订单 {oid}",
                    })
            if order_cards:
                chunks.append(ChatStreamChunk(
                    type="action_buttons",
                    content="请选择要退货的订单：",
                    actions=order_cards,
                ))

        elif len(order_ids_in_response) == 1:
            # 用户已选好或只有一个订单 → 提供确认/取消按钮
            oid = order_ids_in_response[0]
            order_data = next((o for o in orders if str(o.get("order_id", "")).upper() == oid.upper()), None)
            product_name = order_data.get("product", oid) if order_data else oid

            confirm_actions = [
                {
                    "type": "confirm",
                    "label": f"✅ 确认退货",
                    "action": f"确认退货 {oid}",
                    "style": "primary",
                },
                {
                    "type": "cancel",
                    "label": "❌ 取消",
                    "action": "取消退货",
                    "style": "default",
                },
            ]
            chunks.append(ChatStreamChunk(
                type="action_buttons",
                content=f"是否确认退货 {product_name}？",
                actions=confirm_actions,
            ))

        return chunks

    async def _get_or_create_conversation(
        self,
        conversation_id: Optional[UUID],
        user_id: Optional[UUID],
    ) -> Conversation:
        """获取或创建会话"""
        if conversation_id:
            conv = await self.conv_repo.get_by_id(conversation_id)
            if conv:
                return conv

        # 创建新会话
        conv = Conversation(
            user_id=user_id,
            channel=ConversationChannel.WEB,
            status=ConversationStatus.ACTIVE,
        )
        return await self.conv_repo.create(conv)
