"""
订单与商品相关的基础 Tool 集合
供具有 Tool Calling 能力的 Worker 使用
"""

from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
from src.database.session import get_session_factory
from src.models.taobao_user_data import TaobaoUserData
import logging

logger = logging.getLogger(__name__)

@tool
async def query_order(order_id: str) -> str:
    """
    根据给定的订单号 (如 ORD-2024001) 查询详细订单信息、物流状态、预计送达时间等。
    你需要先获取或提取用户的订单号才能调用此工具。
    """
    factory = get_session_factory()
    async with factory() as session:
        # Get the latest taobao user data. In a real system you would filter by the current `user_id` from context.
        stmt = select(TaobaoUserData).order_by(TaobaoUserData.last_synced_at.desc())
        result = await session.execute(stmt)
        taobao_user = result.scalars().first()
        
        if not taobao_user or not taobao_user.orders:
             return f"未找到单号为 {order_id} 的订单，请提醒用户确认。"
             
        orders = taobao_user.orders if isinstance(taobao_user.orders, list) else []
        for order in orders:
            if str(order.get("order_id", "")).upper() == order_id.upper():
                return_status = ""
                if 'return_status' in order:
                    return_status = f"\n退货状态: {order['return_status']}"

                return (
                    f"订单号: {order.get('order_id')}\n"
                    f"商品: {order.get('product')}\n"
                    f"状态: {order.get('status')}\n"
                    f"物流: {order.get('logistics', '暂无')}\n"
                    f"金额: {order.get('amount')}\n"
                    f"预计送达: {order.get('estimated_delivery', '暂无')}"
                    f"{return_status}"
                )

        return f"未找到单号为 {order_id} 的订单，请提醒用户确认。"

@tool
async def query_user_orders() -> str:
    """
    不需要参数。查询当前用户账号下最近购买的历史订单列表。
    当用户说“我最近买了什么”、“帮我查下我的订单”，且未提供具体单号时调用此工具。
    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(TaobaoUserData).order_by(TaobaoUserData.last_synced_at.desc())
        result = await session.execute(stmt)
        taobao_user = result.scalars().first()
        
        if not taobao_user or not taobao_user.orders:
             return "这是当前用户最近的订单摘要：\n当前用户近期没有订单记录。"
             
        orders = taobao_user.orders if isinstance(taobao_user.orders, list) else []
        recent = orders[:3]
        
        parts = ["这是当前用户最近的订单摘要："]
        for o in recent:
            status_display = o.get('status', '未知状态')
            if 'return_status' in o:
                status_display += f" (退货状态: {o['return_status']})"
            parts.append(f"- 【{o.get('order_id')}】商品: {o.get('product')} | 状态: {status_display}")
        parts.append("如果你需要其中某一个订单的详细物流信息，可以选择调用 query_order(order_id)。")
        return "\n".join(parts)

@tool
async def process_return(order_id: str) -> str:
    """
    处理指定订单的退货申请。
    在调用此工具前，必须已经向用户确认过退货意向。
    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(TaobaoUserData).order_by(TaobaoUserData.last_synced_at.desc())
        result = await session.execute(stmt)
        taobao_user = result.scalars().first()
        
        if not taobao_user or not taobao_user.orders:
             return f"未找到单号为 {order_id} 的订单，退货申请失败。"
             
        orders = taobao_user.orders if isinstance(taobao_user.orders, list) else []
        order_found = False
        target_order = None
        
        for idx, order in enumerate(orders):
            if str(order.get("order_id", "")).upper() == order_id.upper():
                order_found = True
                target_order = order
                
                if order.get("status") == "处理中":
                    return f"订单 {order_id} 正在处理中，暂时无法退货。请等待发货后再申请。"

                if order.get("status") == "待付款":
                    return f"订单 {order_id} 尚未付款，无需退货。您可以直接取消订单。"

                if order.get("return_status") == "退货中":
                    return f"订单 {order_id} 的退货申请已在处理中，无需重复提交。退款将在1-3个工作日内退回。"

                # 更新订单状态
                orders[idx]["status"] = "退货中"
                orders[idx]["return_status"] = "退货中"
                break
                
        if not order_found:
            return f"未找到单号为 {order_id} 的订单，退货申请失败。"
            
        # Write back and commit
        taobao_user.orders = orders
        flag_modified(taobao_user, "orders")
        try:
            await session.commit()
            return f"订单 {order_id}（{target_order.get('product')}）的退货申请已成功提交！订单状态已更新为「退货中」，退款将在1-3个工作日内原路退回。请通知用户退货已完成。"
        except Exception as e:
            logger.error("退货更新失败: %s", e)
            await session.rollback()
            return f"订单 {order_id} 退货申请失败，数据库更新异常。"

