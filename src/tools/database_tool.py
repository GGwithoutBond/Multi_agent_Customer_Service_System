"""
订单与商品相关的基础 Tool 集合
供具有 Tool Calling 能力的 Worker 使用
"""

from typing import Optional, Dict, Any, List
from langchain_core.tools import tool

# ==========================================
# 订单相关工具 (Mock Data)
# ==========================================
MOCK_ORDERS = {
    "ORD-2024001": {
        "order_id": "ORD-2024001",
        "product": "iPhone 16 Pro",
        "status": "已发货",
        "logistics": "顺丰速运 SF1234567890",
        "amount": "¥8,999",
        "order_date": "2024-12-01",
        "estimated_delivery": "2024-12-05",
    },
    "ORD-2024002": {
        "order_id": "ORD-2024002",
        "product": "AirPods Pro 2",
        "status": "已签收",
        "logistics": "京东物流 JD0987654321",
        "amount": "¥1,899",
        "order_date": "2024-11-28",
        "estimated_delivery": "2024-12-01",
    },
    "ORD-2024003": {
        "order_id": "ORD-2024003",
        "product": "MacBook Air M3",
        "status": "处理中",
        "logistics": "暂未发货",
        "amount": "¥9,499",
        "order_date": "2024-12-05",
        "estimated_delivery": "2024-12-10",
    },
    "ORD-2024004": {
        "order_id": "ORD-2024004",
        "product": "iPad Pro 13\"",
        "status": "待付款",
        "logistics": "—",
        "amount": "¥10,999",
        "order_date": "2024-12-08",
        "estimated_delivery": "—",
    },
}

@tool
def query_order(order_id: str) -> str:
    """
    根据给定的订单号 (如 ORD-2024001) 查询详细订单信息、物流状态、预计送达时间等。
    你需要先获取或提取用户的订单号才能调用此工具。
    """
    order = MOCK_ORDERS.get(order_id.upper())
    if order:
        # Check if there is a pending return
        return_status = ""
        if 'return_status' in order:
            return_status = f"\n退货状态: {order['return_status']}"

        return (
            f"订单号: {order['order_id']}\n"
            f"商品: {order['product']}\n"
            f"状态: {order['status']}\n"
            f"物流: {order['logistics']}\n"
            f"金额: {order['amount']}\n"
            f"预计送达: {order['estimated_delivery']}"
            f"{return_status}"
        )
    return f"未找到单号为 {order_id} 的订单，请提醒用户确认。"

@tool
def query_user_orders() -> str:
    """
    不需要参数。查询当前用户账号下最近购买的历史订单列表。
    当用户说“我最近买了什么”、“帮我查下我的订单”，且未提供具体单号时调用此工具。
    """
    recent = list(MOCK_ORDERS.values())[:3]
    parts = ["这是当前用户最近的订单摘要："]
    for o in recent:
        status_display = o['status']
        if 'return_status' in o:
            status_display += f" (退货状态: {o['return_status']})"
        parts.append(f"- 【{o['order_id']}】商品: {o['product']} | 状态: {status_display}")
    parts.append("如果你需要其中某一个订单的详细物流信息，可以选择调用 query_order(order_id)。")
    return "\n".join(parts)

@tool
def process_return(order_id: str) -> str:
    """
    处理指定订单的退货申请。
    在调用此工具前，必须已经向用户确认过退货意向。
    """
    order = MOCK_ORDERS.get(order_id.upper())
    if not order:
        return f"未找到单号为 {order_id} 的订单，退货申请失败。"

    if order.get("status") == "处理中":
        return f"订单 {order_id} 正在处理中，暂时无法退货。请等待发货后再申请。"

    if order.get("status") == "待付款":
        return f"订单 {order_id} 尚未付款，无需退货。您可以直接取消订单。"

    if order.get("return_status") == "退货中":
        return f"订单 {order_id} 的退货申请已在处理中，无需重复提交。退款将在1-3个工作日内退回。"

    # 更新订单状态为退货中
    order["status"] = "退货中"
    order["return_status"] = "退货中"

    return f"订单 {order_id}（{order['product']}）的退货申请已成功提交！订单状态已更新为「退货中」，退款将在1-3个工作日内原路退回。请通知用户退货已完成。"

