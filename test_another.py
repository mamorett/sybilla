# test_mcp_client.py - Proper MCP client test
import asyncio
import json
import sys
from mcp.client.stdio import stdio_client

async def test_mcp():
    """Test MCP server properly"""
    print("🚀 Testing MCP server...")
    
    # Start server process
    import subprocess
    server_process = subprocess.Popen(
        [sys.executable, "server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        async with stdio_client(server_process.stdin, server_process.stdout) as (read, write):
            # Initialize
            print("📋 Initializing...")
            init_result = await read.initialize()
            print(f"✅ Initialized: {init_result}")
            
            # List tools
            print("📋 Listing tools...")
            tools = await read.list_tools()
            print(f"✅ Tools: {[t.name for t in tools.tools]}")
            
            # Call analytics tool
            print("📊 Calling get_traffic_analytics...")
            result = await read.call_tool("get_traffic_analytics", {
                "time_range": "24h",
                "group_by": "country", 
                "limit": 10
            })
            print(f"✅ Analytics result: {result}")
            
    finally:
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    asyncio.run(test_mcp())
