"""
图数据库存储模块 (Neo4j)
管理知识图谱的存储和查询
"""

from typing import Any, Optional

from src.core.config import get_settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class GraphStore:
    """Neo4j 图数据库存储"""

    def __init__(self):
        self.settings = get_settings()
        self._driver = None

    async def _get_driver(self):
        """获取 Neo4j 驱动"""
        if self._driver is None:
            from neo4j import AsyncGraphDatabase
            self._driver = AsyncGraphDatabase.driver(
                self.settings.NEO4J_URI,
                auth=(self.settings.NEO4J_USER, self.settings.NEO4J_PASSWORD),
            )
        return self._driver

    async def close(self):
        """关闭连接"""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def query(self, cypher: str, params: Optional[dict] = None) -> list[dict[str, Any]]:
        """执行 Cypher 查询"""
        driver = await self._get_driver()
        async with driver.session() as session:
            result = await session.run(cypher, params or {})
            records = await result.data()
            return records

    async def add_entity(
        self,
        entity_type: str,
        properties: dict[str, Any],
    ) -> None:
        """添加实体节点"""
        props_str = ", ".join(f"n.{k} = ${k}" for k in properties)
        cypher = f"MERGE (n:{entity_type} {{name: $name}}) SET {props_str}"
        await self.query(cypher, properties)

    async def add_relationship(
        self,
        from_type: str,
        from_name: str,
        rel_type: str,
        to_type: str,
        to_name: str,
        properties: Optional[dict] = None,
    ) -> None:
        """添加关系"""
        props = ""
        params: dict[str, Any] = {"from_name": from_name, "to_name": to_name}
        if properties:
            props = " {" + ", ".join(f"{k}: ${k}" for k in properties) + "}"
            params.update(properties)

        cypher = (
            f"MATCH (a:{from_type} {{name: $from_name}}), (b:{to_type} {{name: $to_name}}) "
            f"MERGE (a)-[r:{rel_type}{props}]->(b)"
        )
        await self.query(cypher, params)

    async def search_related(
        self,
        entity_name: str,
        max_depth: int = 2,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """搜索实体的关联信息（多跳查询）"""
        cypher = """
        MATCH path = (n {name: $name})-[*1..%d]-(related)
        RETURN related.name AS name,
               labels(related) AS types,
               [r IN relationships(path) | type(r)] AS relations
        LIMIT %d
        """ % (max_depth, limit)

        return await self.query(cypher, {"name": entity_name})

    async def search_by_keyword(
        self, keyword: str, node_types: Optional[list[str]] = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """按关键词搜索节点"""
        if node_types:
            labels = ":".join(node_types)
            cypher = f"""
            MATCH (n:{labels})
            WHERE n.name CONTAINS $keyword OR n.description CONTAINS $keyword
            RETURN n.name AS name, labels(n) AS types, properties(n) AS props
            LIMIT $limit
            """
        else:
            cypher = """
            MATCH (n)
            WHERE n.name CONTAINS $keyword OR n.description CONTAINS $keyword
            RETURN n.name AS name, labels(n) AS types, properties(n) AS props
            LIMIT $limit
            """
        return await self.query(cypher, {"keyword": keyword, "limit": limit})
