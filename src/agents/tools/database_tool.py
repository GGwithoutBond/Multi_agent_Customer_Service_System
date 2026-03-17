"""
数据库查询工具
Agent 可调用的数据库查询工具
优化 6.1: 对接模拟数据源 & 优化 6.2: 可被 LangChain tool calling 使用
"""

from typing import Optional

from langchain_core.tools import tool

from src.core.logging import get_logger

logger = get_logger(__name__)

# ── 模拟订单数据库 ──
_MOCK_ORDERS = {
    "ORD-2024001": {
        "order_id": "ORD-2024001",
        "user_id": "user001",
        "product": "iPhone 16 Pro",
        "status": "已发货",
        "logistics_company": "顺丰速运",
        "tracking_number": "SF1234567890",
        "amount": 8999,
        "order_date": "2024-12-01",
        "estimated_delivery": "2024-12-05",
        "address": "北京市朝阳区***",
    },
    "ORD-2024002": {
        "order_id": "ORD-2024002",
        "user_id": "user001",
        "product": "AirPods Pro 2",
        "status": "已签收",
        "logistics_company": "京东物流",
        "tracking_number": "JD0987654321",
        "amount": 1899,
        "order_date": "2024-11-28",
        "estimated_delivery": "2024-12-01",
        "address": "北京市朝阳区***",
    },
    "ORD-2024003": {
        "order_id": "ORD-2024003",
        "user_id": "user002",
        "product": "MacBook Air M3",
        "status": "处理中",
        "logistics_company": "暂未发货",
        "tracking_number": "—",
        "amount": 9499,
        "order_date": "2024-12-05",
        "estimated_delivery": "2024-12-10",
        "address": "上海市浦东新区***",
    },
    "ORD-2024004": {
        "order_id": "ORD-2024004",
        "user_id": "user002",
        "product": "iPad Pro 13\"",
        "status": "待付款",
        "logistics_company": "—",
        "tracking_number": "—",
        "amount": 10999,
        "order_date": "2024-12-08",
        "estimated_delivery": "—",
        "address": "上海市浦东新区***",
    },
}

# ── 模拟产品数据库 ──
_MOCK_PRODUCTS = {
    "P001": {"id": "P001", "name": "MacBook Pro 14\"", "price": 12999, "category": "电脑", "stock": 50},
    "P002": {"id": "P002", "name": "iPhone 16 Pro Max", "price": 9999, "category": "手机", "stock": 120},
    "P003": {"id": "P003", "name": "Apple Watch Ultra 2", "price": 5999, "category": "手表", "stock": 30},
    "P004": {"id": "P004", "name": "Vision Pro", "price": 29999, "category": "AR设备", "stock": 10},
    "P005": {"id": "P005", "name": "AirPods Max", "price": 4399, "category": "耳机", "stock": 80},
}


@tool
async def query_order(order_id: str) -> str:
    """
    查询订单信息。

    Args:
        order_id: 订单编号

    Returns:
        订单详情文本
    """
    logger.info("🔍 查询订单: %s", order_id)
    order = _MOCK_ORDERS.get(order_id.upper())
    if order:
        return (
            f"订单号: {order['order_id']}\n"
            f"商品: {order['product']}\n"
            f"状态: {order['status']}\n"
            f"物流: {order['logistics_company']} {order['tracking_number']}\n"
            f"金额: ¥{order['amount']}\n"
            f"下单时间: {order['order_date']}\n"
            f"预计送达: {order['estimated_delivery']}"
        )
    return f"未找到订单 {order_id}。请确认订单号是否正确。"


@tool
async def query_user_orders(user_id: str, limit: int = 5) -> str:
    """
    查询用户的订单列表。

    Args:
        user_id: 用户ID
        limit: 返回的最大订单数

    Returns:
        用户订单列表
    """
    logger.info("🔍 查询用户 %s 的订单列表", user_id)
    user_orders = [o for o in _MOCK_ORDERS.values() if o["user_id"] == user_id]

    if not user_orders:
        return f"用户 {user_id} 暂无订单记录。"

    lines = [f"用户 {user_id} 的订单列表：\n"]
    for o in user_orders[:limit]:
        lines.append(f"• {o['order_id']} | {o['product']} | {o['status']} | ¥{o['amount']}")
    return "\n".join(lines)


@tool
async def query_product(product_id: str) -> str:
    """
    查询产品信息。

    Args:
        product_id: 产品ID

    Returns:
        产品详情文本
    """
    logger.info("🔍 查询产品: %s", product_id)
    product = _MOCK_PRODUCTS.get(product_id.upper())
    if product:
        return (
            f"产品: {product['name']}\n"
            f"价格: ¥{product['price']}\n"
            f"分类: {product['category']}\n"
            f"库存: {product['stock']} 件"
        )
    return f"未找到产品 {product_id}。"


@tool
async def search_products(keyword: str, max_results: int = 5) -> str:
    """
    按关键词搜索产品。

    Args:
        keyword: 搜索关键词
        max_results: 最大返回数量

    Returns:
        搜索结果
    """
    logger.info("🔍 搜索产品: %s", keyword)
    keyword_lower = keyword.lower()
    matches = [
        p for p in _MOCK_PRODUCTS.values()
        if keyword_lower in p["name"].lower() or keyword_lower in p["category"].lower()
    ][:max_results]

    if not matches:
        return f"未找到与 '{keyword}' 相关的产品。"

    lines = ["搜索结果：\n"]
    for p in matches:
        lines.append(f"• {p['name']} | ¥{p['price']} | {p['category']} | 库存{p['stock']}件")
    return "\n".join(lines)



# 导出所有工具供 Worker 使用
ALL_TOOLS = [query_order, query_user_orders, query_product, search_products]


# ── 真实工单服务接入 ──
from src.services.ticket_service import TicketService
from src.database.session import get_session_factory

# 紧急度 → 优先级映射 (仍保留在这里做简单参考或去掉，因为TicketService里已经有了)
_URGENCY_TO_PRIORITY = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "critical",
}

@tool
async def create_ticket(
    description: str,
    issue_type: str = "other",
    conversation_id: str = "",
    user_id: str = "",
    urgency: str = "medium",
    sentiment: str = "neutral",
) -> str:
    """
    创建用户投诉工单，并返回工单号。

    Args:
        description: 投诉详情（用户原话或 Agent 整理的问题描述）
        issue_type: 投诉类型，如 quality（质量）/ service（服务）/ logistics（物流）/ refund（退款）/ other
        conversation_id: 关联的会话 ID
        user_id: 用户 ID（可选）
        urgency: 紧急度 low/medium/high/critical（来自 Orchestrator 分析）
        sentiment: 情感状态 positive/neutral/negative/angry/frustrated

    Returns:
        包含工单号和预计处理时间的提示信息
    """
    factory = get_session_factory()
    async with factory() as db:
        try:
            ticket = await TicketService.create_ticket(
                db=db,
                description=description,
                issue_type=issue_type,
                conversation_id=conversation_id,
                user_id=user_id,
                urgency=urgency,
                sentiment=sentiment
            )
            ticket_id = str(ticket.id)
            priority = ticket.priority.value
            
            # 根据优先级给出不同的预计处理时间
            if priority == "critical":
                eta = "2 小时内"
            elif priority == "high":
                eta = "4 小时内"
            elif priority == "medium":
                eta = "1 个工作日内"
            else:
                eta = "3 个工作日内"

            return (
                f"✅ 投诉工单已成功创建\n"
                f"工单号：**{ticket_id}**\n"
                f"投诉类型：{issue_type}\n"
                f"优先级：{priority}\n"
                f"状态：{ticket.status.value}\n"
                f"预计处理时间：{eta}\n\n"
                f"您可以凭工单号随时查询处理进度。\n"
                f"我们会尽快为您跟进，感谢您的耐心。"
            )
        except Exception as e:
            logger.error(f"创建工单失败: {e}", exc_info=True)
            return f"创建工单失败，请稍后重试。（错误：{str(e)[:60]}）"


@tool
async def query_ticket(ticket_id: str) -> str:
    """
    查询指定工单的处理进度和详情。

    Args:
        ticket_id: 工单编号(UUID)

    Returns:
        工单状态和详情信息
    """
    factory = get_session_factory()
    async with factory() as db:
        try:
            ticket = await TicketService.get_ticket(db, ticket_id)
            if not ticket:
                return f"未找到工单 {ticket_id}。请确认工单号是否正确。"
                
            return (
                f"工单号: {ticket.id}\n"
                f"标题: {ticket.title}\n"
                f"类型: {ticket.issue_type}\n"
                f"优先级: {ticket.priority.value}\n"
                f"当前状态: {ticket.status.value}\n"
                f"创建时间: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"处理备注: {ticket.notes or '暂无'}"
            )
        except Exception as e:
            logger.error(f"查询工单失败: {e}", exc_info=True)
            return "查询工单失败，请确认工单号格式是否正确或稍后重试。"


@tool
async def escalate_ticket(ticket_id: str, reason: str = "") -> str:
    """
    催办或升级工单（当用户非常着急、情绪激动，或者处理超时时调用）。

    Args:
        ticket_id: 工单编号(UUID)
        reason: 升级或催办的原因备注

    Returns:
        处理结果提示
    """
    factory = get_session_factory()
    async with factory() as db:
        try:
            ticket = await TicketService.escalate_ticket(db, ticket_id, reason)
            if not ticket:
                return f"未找到工单 {ticket_id}，无法进行催办。"
                
            return (
                f"✅ 工单 {ticket_id} 已成功催办/升级！\n"
                f"当前优先级: {ticket.priority.value}\n"
                f"当前状态: {ticket.status.value}\n"
                f"已记录催办原因重点跟进，人工客服将尽快优先处理您的诉求。"
            )
        except Exception as e:
            logger.error(f"催办工单失败: {e}", exc_info=True)
            return "催办工单失败，请稍后重试。"


COMPLAINT_TOOLS = [create_ticket, query_ticket, escalate_ticket]
