"""
构建知识图谱
从文档中抽取实体和关系，构建知识图谱
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logging import setup_logging
from src.services.knowledge_service import KnowledgeService


# 示例知识数据
SAMPLE_DOCUMENTS = [
    {
        "content": "我们的智能客服系统支持多渠道接入，包括Web、App和微信。系统基于多智能体协作架构，能够处理FAQ、订单查询、产品咨询等多种业务场景。",
        "metadata": {"source": "product_intro", "category": "系统介绍"},
    },
    {
        "content": "订单查询功能支持通过订单号查询订单状态、物流信息。用户可以在聊天界面直接输入订单号进行查询，系统会自动识别并调用订单查询服务。",
        "metadata": {"source": "faq", "category": "订单相关"},
    },
    {
        "content": "如需退货退款，请在收到商品7天内提交申请。退款将在审核通过后3-5个工作日内原路返回。具体退款进度可通过订单详情页查看。",
        "metadata": {"source": "faq", "category": "售后服务"},
    },
]

SAMPLE_ENTITIES = [
    {"type": "Product", "properties": {"name": "智能客服系统", "description": "多智能体协作的智能客服系统"}},
    {"type": "Feature", "properties": {"name": "多渠道接入", "description": "支持Web、App、微信等多种接入渠道"}},
    {"type": "Feature", "properties": {"name": "订单查询", "description": "通过订单号查询订单状态和物流信息"}},
    {"type": "FAQ", "properties": {"name": "退货退款", "description": "收到商品7天内可提交退货退款申请"}},
]

SAMPLE_RELATIONSHIPS = [
    {"from_type": "Product", "from_name": "智能客服系统", "rel_type": "HAS_FEATURE", "to_type": "Feature", "to_name": "多渠道接入"},
    {"from_type": "Product", "from_name": "智能客服系统", "rel_type": "HAS_FEATURE", "to_type": "Feature", "to_name": "订单查询"},
    {"from_type": "FAQ", "from_name": "退货退款", "rel_type": "RELATES_TO", "to_type": "Feature", "to_name": "订单查询"},
]


async def build_knowledge():
    """构建知识图谱"""
    setup_logging()
    service = KnowledgeService()

    print("正在索引文档...")
    count = await service.index_documents(SAMPLE_DOCUMENTS, chunk_size=300)
    print(f"已索引 {count} 个文档块")

    print("正在构建知识图谱...")
    await service.index_knowledge_graph(SAMPLE_ENTITIES, SAMPLE_RELATIONSHIPS)
    print("知识图谱构建完成!")


if __name__ == "__main__":
    asyncio.run(build_knowledge())
