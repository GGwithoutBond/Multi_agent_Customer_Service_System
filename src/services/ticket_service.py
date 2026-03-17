"""
工单服务
处理工单的创建、查询、更新和催办逻辑
"""

from typing import Sequence
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.database.session import get_db_session
from src.models.ticket import Ticket, TicketPriority, TicketStatus

logger = get_logger(__name__)

# 紧急度 -> 优先级映射
_URGENCY_TO_PRIORITY = {
    "low": TicketPriority.LOW,
    "medium": TicketPriority.MEDIUM,
    "high": TicketPriority.HIGH,
    "critical": TicketPriority.CRITICAL,
}


class TicketService:

    @staticmethod
    async def create_ticket(
        db: AsyncSession,
        description: str,
        issue_type: str = "other",
        conversation_id: str = "",
        user_id: str | None = None,
        urgency: str = "medium",
        sentiment: str = "neutral",
    ) -> Ticket:
        """创建新工单"""
        priority = _URGENCY_TO_PRIORITY.get(urgency, TicketPriority.MEDIUM)
        
        # 简单生成一个友好的标题
        title = f"{issue_type.capitalize()} Complaint"
        if len(description) > 0:
            title = description[:20] + ("..." if len(description) > 20 else "")

        db_ticket = Ticket(
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            description=description,
            issue_type=issue_type,
            sentiment=sentiment,
            status=TicketStatus.OPEN,
            priority=priority,
        )
        db.add(db_ticket)
        await db.commit()
        await db.refresh(db_ticket)
        logger.info(f"Ticket created: {db_ticket.id} | priority={priority}")
        return db_ticket

    @staticmethod
    async def get_ticket(db: AsyncSession, ticket_id: str) -> Ticket | None:
        """获取单个工单"""
        try:
            # 校验 uuid 格式
            ticket_uuid = uuid.UUID(ticket_id)
        except ValueError:
            return None
            
        stmt = select(Ticket).where(Ticket.id == ticket_uuid)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_tickets(db: AsyncSession, user_id: str, limit: int = 5) -> Sequence[Ticket]:
        """查询用户的工单列表"""
        stmt = select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def update_status(db: AsyncSession, ticket_id: str, status: TicketStatus, notes: str | None = None) -> Ticket | None:
        """更新工单状态"""
        ticket = await TicketService.get_ticket(db, ticket_id)
        if not ticket:
            return None
        
        ticket.status = status
        if notes:
            if ticket.notes:
                ticket.notes += f"\n{notes}"
            else:
                ticket.notes = notes
                
        await db.commit()
        await db.refresh(ticket)
        return ticket

    @staticmethod
    async def escalate_ticket(db: AsyncSession, ticket_id: str, reason: str = "") -> Ticket | None:
        """
        工单催办/升级
        普通 -> 高优先级，高优先级 -> 严重优先级
        或者直接把状态改为 ESCALATED 让人工介入
        """
        ticket = await TicketService.get_ticket(db, ticket_id)
        if not ticket:
            return None
            
        # 调整优先级
        if ticket.priority == TicketPriority.LOW:
            ticket.priority = TicketPriority.MEDIUM
        elif ticket.priority == TicketPriority.MEDIUM:
            ticket.priority = TicketPriority.HIGH
        elif ticket.priority == TicketPriority.HIGH:
            ticket.priority = TicketPriority.CRITICAL

        # 记录催办原因
        escalation_note = f"[Escalated] Reason: {reason}" if reason else "[Escalated]"
        if ticket.notes:
            ticket.notes += f"\n{escalation_note}"
        else:
            ticket.notes = escalation_note
            
        # 如果已经是最高优先级，或者用户非常急迫，可以将状态置为 ESCALATED
        if ticket.priority == TicketPriority.CRITICAL and ticket.status != TicketStatus.RESOLVED and ticket.status != TicketStatus.CLOSED:
            ticket.status = TicketStatus.ESCALATED
            
        await db.commit()
        await db.refresh(ticket)
        return ticket
