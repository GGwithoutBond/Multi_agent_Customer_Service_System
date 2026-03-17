import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.agents.tools.mcp_client import taobao_mcp_session

async def test():
    print("Testing taobao_mcp_session...")
    async with taobao_mcp_session() as (session, tools):
        if session and tools:
            print(f"Successfully loaded {len(tools)} tools.")
            for tool in tools:
                print(f"- {tool.name}")
        else:
            print("Failed to load session/tools.")

if __name__ == "__main__":
    asyncio.run(test())
