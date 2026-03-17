import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    url = "http://localhost:3654/mcp"
    print(f"Connecting to {url}...")

    try:
        async with streamable_http_client(url) as transport:
            print("transport:", type(transport), transport)

            if isinstance(transport, tuple):
                print("tuple len:", len(transport))
                read_stream = transport[0]
                write_stream = transport[1]
            else:
                raise TypeError(f"Unexpected transport type: {type(transport)}")

            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()

                print("\nAvailable MCP Tools:\n")
                for tool in tools.tools:
                    print(f"- {tool.name}: {tool.description}")

    except Exception:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())