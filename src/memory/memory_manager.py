"""
记忆管理器
统一管理三级记忆系统（工作记忆、短期记忆、长期记忆）
优化: 自动提取用户画像、工作记忆实际使用
"""

import json
from typing import Any, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.logging import get_logger
from src.llm import get_llm_client
from src.llm.prompt_templates import MEMORY_SUMMARY_PROMPT, USER_PROFILE_EXTRACTION_PROMPT
from src.memory.long_term_memory import LongTermMemory
from src.memory.short_term_memory import ShortTermMemory
from src.memory.working_memory import WorkingMemory

logger = get_logger(__name__)


class MemoryManager:
    """
    记忆管理器
    协调工作记忆、短期记忆、长期记忆的加载和存储
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.working = WorkingMemory()
        self.short_term = ShortTermMemory()
        self._long_term: Optional[LongTermMemory] = None
        if db_session:
            self._long_term = LongTermMemory(db_session)

    async def load_context(
        self,
        conversation_id: str,
        user_id: Optional[str] = None,
    ) -> list[BaseMessage]:
        """
        加载对话上下文，返回 LangChain 消息列表

        流程:
        1. 从短期记忆加载当前会话历史
        2. 检查是否有会话摘要
        3. 如有长期记忆，加载用户画像
        """
        messages: list[BaseMessage] = []

        # 1. 加载会话摘要
        summary = await self.short_term.get_summary(conversation_id)
        if summary:
            messages.append(SystemMessage(content=f"之前的对话摘要: {summary}"))

        # 2. 加载短期记忆（对话历史）
        history = await self.short_term.load(conversation_id)
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))

        # 3. 加载长期记忆（用户画像）
        if self._long_term and user_id:
            profile_data = await self._long_term.load(user_id)
            if profile_data:
                profile_info = profile_data[0]
                profile_parts = []
                if profile_info.get("preferences"):
                    profile_parts.append(f"用户偏好: {profile_info['preferences']}")
                if profile_info.get("entities"):
                    profile_parts.append(f"关键实体: {profile_info['entities']}")
                if profile_info.get("tags"):
                    profile_parts.append(f"用户标签: {', '.join(profile_info['tags'])}")
                if profile_info.get("interaction_summary"):
                    profile_parts.append(f"历史交互: {profile_info['interaction_summary']}")
                if profile_parts:
                    context_msg = "用户画像:\n" + "\n".join(profile_parts)
                    messages.insert(0, SystemMessage(content=context_msg))

        return messages

    async def save_turn(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        user_id: Optional[str] = None,
    ) -> None:
        """保存一轮对话到短期记忆，并异步更新用户画像"""
        await self.short_term.add_message(conversation_id, {
            "role": "user",
            "content": user_message,
        })
        await self.short_term.add_message(conversation_id, {
            "role": "assistant",
            "content": assistant_message,
        })

        # 检查是否需要摘要压缩
        settings = get_settings()
        history = await self.short_term.load(conversation_id)
        turn_count = len(history) // 2
        if turn_count >= settings.MEMORY_SUMMARY_THRESHOLD:
            await self._compress_to_summary(conversation_id, history)

        # ── Fix 7: 异步后台提取用户画像（不阻塞响应返回） ──
        if user_id and self._long_term:
            import asyncio
            asyncio.create_task(
                self._safe_extract_profile(user_id, user_message, assistant_message)
            )

    async def _compress_to_summary(
        self, conversation_id: str, history: list[dict[str, Any]]
    ) -> None:
        """将早期对话压缩为摘要"""
        try:
            # 取出前半部分进行摘要
            split_point = len(history) // 2
            early_history = history[:split_point]
            recent_history = history[split_point:]

            # 构建摘要请求
            history_text = "\n".join(
                f"{msg['role']}: {msg['content']}" for msg in early_history
            )
            prompt = MEMORY_SUMMARY_PROMPT.format(conversation_history=history_text)

            llm_client = get_llm_client()
            summary = await llm_client.invoke([HumanMessage(content=prompt)])

            # 如果已有旧摘要，将旧摘要也纳入 LLM 压缩，而非简单拼接追加
            existing_summary = await self.short_term.get_summary(conversation_id)
            if existing_summary:
                # 把旧摘要和新对话一起重新压缩为一份简洁摘要（覆盖而非追加）
                combined_history = f"[历史摘要]\n{existing_summary}\n\n[最新对话]\n{history_text}"
                prompt = MEMORY_SUMMARY_PROMPT.format(conversation_history=combined_history)
                summary = await llm_client.invoke([HumanMessage(content=prompt)])

            # 限制摘要最大长度，避免超出 context（截断保留最后部分）
            MAX_SUMMARY_LENGTH = 1000
            if len(summary) > MAX_SUMMARY_LENGTH:
                summary = summary[-MAX_SUMMARY_LENGTH:]
                logger.debug("摘要超长，已截断至 %d 字符", MAX_SUMMARY_LENGTH)

            await self.short_term.set_summary(conversation_id, summary)
            await self.short_term.save(conversation_id, recent_history)

            logger.info("会话 %s 的记忆已压缩为摘要", conversation_id)
        except Exception as e:
            logger.warning("记忆压缩失败: %s", e)

    async def _safe_extract_profile(
        self,
        user_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """后台安全执行画像提取（不抛异常，防止 create_task 未处理的异常告警）"""
        try:
            await self._extract_and_update_profile(user_id, user_message, assistant_message)
        except Exception as e:
            logger.warning("用户画像后台更新失败: %s", e)

    async def _extract_and_update_profile(
        self,
        user_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """
        优化 3.2: 从对话中自动提取用户画像信息并更新
        """
        try:
            llm_client = get_llm_client()
            prompt = USER_PROFILE_EXTRACTION_PROMPT.format(
                user_message=user_message,
                assistant_message=assistant_message,
            )
            result = await llm_client.invoke([HumanMessage(content=prompt)])

            # 解析 JSON
            result = result.strip()
            if "```" in result:
                start = result.find("{")
                end = result.rfind("}") + 1
                if start != -1 and end > start:
                    result = result[start:end]

            profile_data = json.loads(result)

            # 只在有有效数据时更新
            preferences = profile_data.get("preferences", {})
            entities = profile_data.get("entities", {})
            tags = profile_data.get("tags", [])

            if not preferences and not entities and not tags:
                return  # 无可提取信息，跳过

            await self.update_user_profile(
                user_id=user_id,
                preferences=preferences if preferences else None,
                entities=entities if entities else None,
                tags=tags if tags else None,
            )
            logger.debug("用户画像已更新: user=%s", user_id)

        except json.JSONDecodeError:
            logger.debug("画像提取返回非 JSON，跳过")
        except Exception as e:
            logger.debug("用户画像提取失败: %s", e)

    async def update_user_profile(
        self,
        user_id: str,
        entities: Optional[dict] = None,
        preferences: Optional[dict] = None,
        tags: Optional[list[str]] = None,
    ) -> None:
        """更新用户长期画像"""
        if not self._long_term:
            return

        data: dict[str, Any] = {}
        if entities:
            data["entities"] = entities
        if preferences:
            data["preferences"] = preferences
        if tags:
            data["tags"] = tags

        if data:
            await self._long_term.save(user_id, [data])

    async def clear_session(self, conversation_id: str) -> None:
        """清除会话的短期记忆"""
        await self.short_term.clear(conversation_id)
        self.working.reset()
