#!/usr/bin/env python3
"""
Diagnostic MCP Analytics Test - Deep debugging version
Run with: python diagnostic_test.py
"""

import json
import subprocess
import logging
import sys
import asyncio
import os
from typing import Dict, Any, List

# Configure detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DiagnosticMCPClient:
    def __init__(self, server_script_path: str = None):
        # Find server script
        if server_script_path:
            self.server_script_path = server_script_path
        elif os.getenv("MCP_SERVER_SCRIPT_PATH"):
            self.server_script_path = os.getenv("MCP_SERVER_SCRIPT_PATH")
        else:
            possible_paths = ["server.py", "mcp_server.py", "app/server.py", "../server.py"]
            self.server_script_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    self.server_script_path = path
                    break
            
            if not self.server_script_path:
                raise FileNotFoundError("Could not find MCP server script. Please specify path.")
        
        self.request_id = 0
        print(f"📍 Using server script: {self.server_script_path}")
    
    async def _call_server_with_debug(self, request: dict) -> dict:
        """Call server with full debugging output"""
        try:
            self.request_id += 1
            request["id"] = self.request_id
            
            request_json = json.dumps(request, indent=2)
            print(f"\n🔍 SENDING REQUEST:")
            print(f"{'='*50}")
            print(request_json)
            print(f"{'='*50}")
            
            # Execute server script
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [sys.executable, self.server_script_path],
                    input=request_json,
                    text=True,
                    capture_output=True,
                    timeout=120
                )
            )
            
            print(f"\n📤 SERVER RESPONSE:")
            print(f"Return code: {result.returncode}")
            print(f"STDOUT length: {len(result.stdout)} chars")
            print(f"STDERR length: {len(result.stderr)} chars")
            
            if result.stderr:
                print(f"\n🚨 STDERR:")
                print(result.stderr)
            
            print(f"\n📋 FULL STDOUT:")
            print(f"{'='*50}")
            print(result.stdout)
            print(f"{'='*50}")
            
            if result.returncode != 0:
                return {"error": f"Server error (code {result.returncode}): {result.stderr}"}
            
            # Try to parse JSON responses
            responses = []
            for line_num, line in enumerate(result.stdout.strip().split('\n'), 1):
                line = line.strip()
                if line.startswith('{') and '"jsonrpc"' in line:
                    try:
                        parsed = json.loads(line)
                        responses.append(parsed)
                        print(f"\n✅ PARSED JSON (line {line_num}):")
                        print(json.dumps(parsed, indent=2))
                    except json.JSONDecodeError as e:
                        print(f"\n❌ JSON PARSE ERROR (line {line_num}): {e}")
                        print(f"Line content: {line[:200]}...")
            
            if responses:
                return responses[-1]  # Return last response
            else:
                return {"error": f"No valid JSON response found", "raw_output": result.stdout}
            
        except Exception as e:
            print(f"\n❌ REQUEST EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    async def test_basic_connection(self):
        """Test basic MCP connection"""
        print(f"\n{'='*60}")
        print("🔌 TESTING BASIC CONNECTION")
        print(f"{'='*60}")
        
        response = await self._call_server_with_debug({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "diagnostic-client", "version": "1.0.0"}
            }
        })
        
        success = "result" in response and "error" not in response
        print(f"\n🔌 Connection result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        return success
    
    async def test_list_tools(self):
        """Test tools listing"""
        print(f"\n{'='*60}")
        print("📋 TESTING TOOLS LIST")
        print(f"{'='*60}")
        
        response = await self._call_server_with_debug({
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {}
        })
        
        if "error" in response:
            print(f"❌ Tools list failed: {response['error']}")
            return []
        
        tools = response.get("result", {}).get("tools", [])
        print(f"\n📋 Found {len(tools)} tools:")
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool.get('name', 'Unknown')} - {tool.get('description', 'No description')}")
        
        return tools
    
    async def test_raw_analytics_call(self, group_by: str = "country"):
        """Test raw analytics call with full debugging"""
        print(f"\n{'='*60}")
        print(f"🔍 TESTING RAW ANALYTICS CALL - GROUP BY: {group_by}")
        print(f"{'='*60}")
        
        response = await self._call_server_with_debug({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get_traffic_analytics",
                "arguments": {
                    "time_range": "24h",
                    "group_by": group_by,
                    "limit": 100
                }
            }
        })
        
        print(f"\n🔍 ANALYTICS RESPONSE ANALYSIS:")
        print(f"Response type: {type(response)}")
        print(f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
        
        if "error" in response:
            print(f"❌ Analytics call failed: {response['error']}")
            return response
        
        # Analyze the result structure
        result = response.get("result", {})
        print(f"\nResult keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        if "content" in result:
            content = result["content"]
            print(f"Content type: {type(content)}")
            print(f"Content length: {len(content) if isinstance(content, (list, dict)) else 'Not countable'}")
            
            if isinstance(content, list):
                for i, item in enumerate(content):
                    print(f"\nContent item {i}:")
                    print(f"  Type: {item.get('type', 'Unknown')}")
                    if item.get("type") == "text":
                        text_content = item.get("text", "")
                        print(f"  Text length: {len(text_content)}")
                        print(f"  Text preview: {text_content[:200]}...")
                        
                        # Try to parse as JSON
                        try:
                            parsed_data = json.loads(text_content)
                            print(f"  ✅ JSON parsed successfully")
                            print(f"  Data type: {type(parsed_data)}")
                            if isinstance(parsed_data, dict):
                                print(f"  Data keys: {list(parsed_data.keys())}")
                                
                                # Look for the specific grouping data
                                group_key = f"top_{group_by}"
                                if group_key in parsed_data:
                                    group_data = parsed_data[group_key]
                                    print(f"  🎯 Found {group_key}: {len(group_data) if isinstance(group_data, list) else 'Not a list'} items")
                                    if isinstance(group_data, list) and group_data:
                                        print(f"  Sample item: {group_data[0]}")
                                else:
                                    print(f"  ❌ {group_key} not found in data")
                                
                                # Check raw counts
                                if "raw_counts" in parsed_data:
                                    print(f"  📊 Raw counts: {parsed_data['raw_counts']}")
                                
                        except json.JSONDecodeError as e:
                            print(f"  ❌ JSON parse failed: {e}")
        
        return response
    
    async def test_simple_country_search(self):
        """Test a simple country search to see if we get any data"""
        print(f"\n{'='*60}")
        print("🌍 TESTING SIMPLE COUNTRY SEARCH")
        print(f"{'='*60}")
        
        response = await self._call_server_with_debug({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_logs_by_country",
                "arguments": {
                    "country": "US",
                    "time_range": "24h",
                    "limit": 10
                }
            }
        })
        
        print(f"\n🌍 COUNTRY SEARCH ANALYSIS:")
        if "error" in response:
            print(f"❌ Country search failed: {response['error']}")
        else:
            result = response.get("result", {})
            if "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        try:
                            data = json.loads(item["text"])
                            if isinstance(data, dict) and "logs" in data:
                                logs = data["logs"]
                                print(f"✅ Found {len(logs)} logs for US")
                                if logs:
                                    print(f"Sample log: {logs[0]}")
                            else:
                                print(f"Data structure: {type(data)}, keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")
                        except:
                            print(f"Raw text: {item['text'][:200]}...")
        
        return response

async def run_full_diagnostic(server_path: str = None):
    """Run complete diagnostic test"""
    print("🚀 STARTING FULL MCP DIAGNOSTIC")
    print("This will show exactly what's happening with your MCP server")
    
    try:
        client = DiagnosticMCPClient(server_path)
        
        # Test 1: Basic connection
        if not await client.test_basic_connection():
            print("❌ Basic connection failed - stopping here")
            return
        
        # Test 2: List tools
        tools = await client.test_list_tools()
        if not tools:
            print("❌ No tools found - stopping here")
            return
        
        # Test 3: Simple country search (to see if we get any data at all)
        await client.test_simple_country_search()
        
        # Test 4: Raw analytics calls for each grouping
        groupings = ["country", "city", "sensor", "isp"]
        for group_by in groupings:
            await client.test_raw_analytics_call(group_by)
        
        print(f"\n{'='*60}")
        print("🏁 DIAGNOSTIC COMPLETE")
        print("Check the output above to see exactly what your server is returning")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Diagnostic MCP Analytics Test")
    parser.add_argument("--server", "-s", help="Path to MCP server script")
    parser.add_argument("--group", "-g", help="Test only specific grouping")
    
    args = parser.parse_args()
    
    if args.group:
        async def test_single():
            client = DiagnosticMCPClient(args.server)
            await client.test_basic_connection()
            await client.test_raw_analytics_call(args.group)
        asyncio.run(test_single())
    else:
        asyncio.run(run_full_diagnostic(args.server))

if __name__ == "__main__":
    main()
