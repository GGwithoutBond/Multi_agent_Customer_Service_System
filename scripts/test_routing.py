import asyncio
import os
import sys

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.orchestrator.router import route_decision

async def main():
    query = "查看一下当前淘宝用户的信息"
    print(f"Query: {query}")
    decision = await route_decision(query)
    print(f"Decision: {decision}")

if __name__ == "__main__":
    asyncio.run(main())
