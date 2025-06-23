#!/usr/bin/env python3
"""
Standalone test script for MCP analytics groupings
Run with: python test_groupings.py
"""

import json
import subprocess
import logging
import sys
import asyncio
import os
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StandaloneMCPClient:
    def __init__(self, server_script_path: str = None):
        # Try to find server script path
        if server_script_path:
            self.server_script_path = server_script_path
        elif os.getenv("MCP_SERVER_SCRIPT_PATH"):
            self.server_script_path = os.getenv("MCP_SERVER_SCRIPT_PATH")
        else:
            # Try common locations
            possible_paths = [
                "server.py",
                "mcp_server.py", 
                "app/server.py",
                "../server.py"
            ]
            self.server_script_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    self.server_script_path = path
                    break
            
            if not self.server_script_path:
                raise FileNotFoundError("Could not find MCP server script. Please specify path.")
        
        self.request_id = 0
        print(f"📍 Using server script: {self.server_script_path}")
    
    async def _call_server_simple(self, request: dict) -> dict:
        """Call MCP server with JSON-RPC request"""
        try:
            self.request_id += 1
            request["id"] = self.request_id
            
            request_json = json.dumps(request)
            
            # Execute server script with input
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [sys.executable, self.server_script_path],
                    input=request_json,
                    text=True,
                    capture_output=True,
                    timeout=60  # Increased timeout for analytics
                )
            )
            
            if result.returncode != 0:
                return {"error": f"Server error (code {result.returncode}): {result.stderr}"}
            
            # Parse response - look for JSON-RPC response
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith('{') and '"jsonrpc"' in line:
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON line: {line[:100]}...")
                        continue
            
            return {"error": f"No valid JSON response found. Output: {result.stdout[:200]}..."}
            
        except subprocess.TimeoutExpired:
            return {"error": "Server request timed out"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    async def initialize(self) -> bool:
        """Initialize MCP connection"""
        try:
            response = await self._call_server_simple({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            })
            
            if "error" in response:
                logger.error(f"❌ Initialize failed: {response['error']}")
                return False
            
            logger.info("✅ MCP connection initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialize exception: {e}")
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        try:
            response = await self._call_server_simple({
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {}
            })
            
            if "error" in response:
                logger.error(f"❌ List tools failed: {response['error']}")
                return []
            
            tools = response.get("result", {}).get("tools", [])
            logger.info(f"📋 Found {len(tools)} tools")
            return tools
            
        except Exception as e:
            logger.error(f"❌ List tools exception: {e}")
            return []
    
    async def get_traffic_analytics_by_group(self, group_by: str = "country", time_range: str = "24h", limit: int = 1000) -> dict:
        """Get analytics grouped by different dimensions"""
        try:
            logger.info(f"🔍 Requesting analytics: group_by={group_by}, time_range={time_range}, limit={limit}")
            
            # Call analytics tool
            tool_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_traffic_analytics",
                    "arguments": {
                        "time_range": time_range,
                        "group_by": group_by,
                        "limit": limit
                    }
                }
            }
            
            response = await self._call_server_simple(tool_request)
            
            if "error" in response:
                return {"error": response["error"]}
            
            # Extract data from MCP response
            result = response.get("result", {})
            if "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        try:
                            data = json.loads(item["text"])
                            return data
                        except json.JSONDecodeError as parse_error:
                            logger.warning(f"🔍 JSON parse failed: {parse_error}")
                            return {"raw": item["text"], "parse_error": str(parse_error)}
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Analytics failed: {e}")
            return {"error": str(e)}

async def test_single_grouping(client: StandaloneMCPClient, group_by: str, time_range: str = "24h", limit: int = 1000) -> Dict[str, Any]:
    """Test a single grouping type"""
    print(f"\n{'='*60}")
    print(f"🔍 Testing {group_by.upper()} grouping")
    print(f"   Time range: {time_range}")
    print(f"   Limit: {limit}")
    print(f"{'='*60}")
    
    result = await client.get_traffic_analytics_by_group(
        group_by=group_by, 
        time_range=time_range, 
        limit=limit
    )
    
    if "error" in result:
        print(f"❌ {group_by} FAILED: {result['error']}")
        return {"status": "failed", "error": result["error"]}
    
    # Analyze results
    analysis = {
        "status": "success",
        "group_by": group_by,
        "total_requests": result.get('total_requests', 0),
        "unique_items": 0,
        "top_items_count": 0,
        "has_distribution": False,
        "raw_counts": result.get('raw_counts', {}),
        "sample_data": {}
    }
    
    # Check for grouped data
    top_key = f"top_{group_by}"
    if top_key in result:
        top_items = result[top_key]
        analysis["top_items_count"] = len(top_items)
        analysis["sample_data"]["top_3"] = top_items[:3] if top_items else []
    
    # Check for distribution data
    dist_key = f"{group_by}_distribution"
    if dist_key in result:
        distribution = result[dist_key]
        analysis["has_distribution"] = bool(distribution)
        analysis["unique_items"] = len(distribution)
        analysis["sample_data"]["distribution_sample"] = dict(list(distribution.items())[:3]) if distribution else {}
    
    # Check unique counts
    unique_key = f"unique_{group_by}s"
    if unique_key in result:
        analysis["unique_items"] = result[unique_key]
    
    # Print results
    print(f"✅ {group_by.upper()} SUCCESS:")
    print(f"   📊 Total requests: {analysis['total_requests']}")
    print(f"   🎯 Unique {group_by}s: {analysis['unique_items']}")
    print(f"   📋 Top items found: {analysis['top_items_count']}")
    print(f"   📈 Has distribution: {analysis['has_distribution']}")
    
    if analysis["sample_data"].get("top_3"):
        print(f"   🏆 Top 3 {group_by}s:")
        for i, item in enumerate(analysis["sample_data"]["top_3"], 1):
            print(f"      {i}. {item.get('name', 'Unknown')}: {item.get('count', 0)} requests")
    
    if analysis["raw_counts"]:
        print(f"   🔢 Raw counts: {analysis['raw_counts']}")
    
    return analysis

async def test_all_groupings(server_path: str = None, time_range: str = "24h", limit: int = 1000):
    """Test all grouping types"""
    print("🚀 Starting MCP Analytics Grouping Test")
    print(f"⏰ Time range: {time_range}")
    print(f"📊 Limit: {limit}")
    
    try:
        # Initialize client
        client = StandaloneMCPClient(server_path)
        
        # Test connection
        if not await client.initialize():
            print("❌ Failed to initialize MCP client")
            return
        
        # List available tools
        tools = await client.list_tools()
        tool_names = [tool.get("name", "unknown") for tool in tools]
        print(f"📋 Available tools: {', '.join(tool_names)}")
        
        if "get_traffic_analytics" not in tool_names:
            print("❌ get_traffic_analytics tool not found!")
            return
        
        # Test each grouping type
        groupings = ["country", "city", "sensor", "isp"]
        results = {}
        
        for group_by in groupings:
            try:
                result = await test_single_grouping(client, group_by, time_range, limit)
                results[group_by] = result
            except Exception as e:
                print(f"❌ Exception testing {group_by}: {e}")
                results[group_by] = {"status": "exception", "error": str(e)}
        
        # Summary
        print(f"\n{'='*60}")
        print("📊 FINAL SUMMARY")
        print(f"{'='*60}")
        
        successful = [g for g, r in results.items() if r.get("status") == "success"]
        failed = [g for g, r in results.items() if r.get("status") != "success"]
        
        print(f"✅ Successful groupings ({len(successful)}): {', '.join(successful)}")
        if failed:
            print(f"❌ Failed groupings ({len(failed)}): {', '.join(failed)}")
        
        # Detailed failure analysis
        if failed:
            print(f"\n🔍 FAILURE ANALYSIS:")
            for group_by in failed:
                result = results[group_by]
                print(f"   {group_by}: {result.get('error', 'Unknown error')}")
        
        # Success details
        if successful:
            print(f"\n🎯 SUCCESS DETAILS:")
            for group_by in successful:
                result = results[group_by]
                print(f"   {group_by}: {result['unique_items']} unique items, {result['top_items_count']} top items")
        
        return results
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function with command line argument support"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test MCP Analytics Groupings")
    parser.add_argument("--server", "-s", help="Path to MCP server script")
    parser.add_argument("--time-range", "-t", default="24h", help="Time range (default: 24h)")
    parser.add_argument("--limit", "-l", type=int, default=1000, help="Query limit (default: 1000)")
    parser.add_argument("--group", "-g", help="Test only specific grouping (country, city, sensor, isp)")
    
    args = parser.parse_args()
    
    if args.group:
        # Test single grouping
        async def test_single():
            client = StandaloneMCPClient(args.server)
            if await client.initialize():
                await test_single_grouping(client, args.group, args.time_range, args.limit)
        
        asyncio.run(test_single())
    else:
        # Test all groupings
        asyncio.run(test_all_groupings(args.server, args.time_range, args.limit))

if __name__ == "__main__":
    main()
