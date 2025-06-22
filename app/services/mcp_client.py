# app/services/mcp_client.py
import json
import subprocess
import logging
import sys
import asyncio
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self):
        self.server_script_path = settings.MCP_SERVER_SCRIPT_PATH
        self.request_id = 0
    
    async def _call_server_simple(self, request: dict) -> dict:
        """Exactly like your working echo test"""
        try:
            self.request_id += 1
            request["id"] = self.request_id
            
            request_json = json.dumps(request)
            
            # EXACTLY like: echo '...' | python server.py
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    [sys.executable, self.server_script_path],
                    input=request_json,
                    text=True,
                    capture_output=True,
                    timeout=30
                )
            )
            
            if result.returncode != 0:
                return {"error": f"Server error: {result.stderr}"}
            
            # Parse response
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if line.startswith('{') and '"jsonrpc"' in line:
                    try:
                        return json.loads(line)
                    except:
                        continue
            
            return {"error": "No valid JSON response"}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def test_connection(self) -> bool:
        """Test with initialize"""
        try:
            response = await self._call_server_simple({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            })
            
            success = "result" in response and "error" not in response
            if success:
                logger.info("✅ MCP connection successful")
            else:
                logger.error(f"❌ MCP failed: {response}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List tools"""
        try:
            # Initialize first
            init_response = await self._call_server_simple({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            })
            
            if "error" in init_response:
                return []
            
            # List tools
            tools_response = await self._call_server_simple({
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {}
            })
            
            if "error" in tools_response:
                return []
            
            return tools_response.get("result", {}).get("tools", [])
            
        except Exception as e:
            logger.error(f"List tools failed: {e}")
            return []
    
# In your mcp_client.py, update the get_traffic_analytics method:

    async def get_traffic_analytics(self, time_range: str = "24h", limit: int = 1000, **kwargs) -> dict:
        """Get analytics with detailed debugging"""
        try:
            logger.info(f"🔍 Requesting analytics: time_range={time_range}, limit={limit}")
            
            # Initialize
            init_response = await self._call_server_simple({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            })
            
            logger.info(f"🔍 Initialize response: {init_response}")
            
            if "error" in init_response:
                return {"error": init_response["error"]}
            
            # Call tool
            tool_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_traffic_analytics",
                    "arguments": {
                        "time_range": time_range,
                        "group_by": "country",
                        "limit": limit
                    }
                }
            }
            
            logger.info(f"🔍 Tool request: {json.dumps(tool_request, indent=2)}")
            
            response = await self._call_server_simple(tool_request)
            
            logger.info(f"🔍 Tool response: {json.dumps(response, indent=2)}")
            
            if "error" in response:
                return {"error": response["error"]}
            
            # Extract data
            result = response.get("result", {})
            if "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        try:
                            data = json.loads(item["text"])
                            logger.info(f"🔍 Parsed data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                            return data
                        except Exception as parse_error:
                            logger.warning(f"🔍 JSON parse failed: {parse_error}")
                            return {"raw": item["text"]}
            
            logger.info(f"🔍 Raw result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Analytics failed: {e}")
            return {"error": str(e)}


    async def search_logs_by_country(self, country: str = None, country_code: str = None, time_range: str = "24h", limit: int = 100) -> dict:
        """Search by country - accepts both 'country' and 'country_code' parameters"""
        try:
            # Use whichever parameter was provided
            search_country = country or country_code
            if not search_country:
                return {"error": "Either 'country' or 'country_code' parameter is required"}
            
            await self._call_server_simple({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            })
            
            response = await self._call_server_simple({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "search_logs_by_country",
                    "arguments": {
                        "country": search_country,  # Your server expects 'country'
                        "time_range": time_range,
                        "limit": limit
                    }
                }
            })
            
            if "error" in response:
                return {"error": response["error"]}
            
            result = response.get("result", {})
            if "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        try:
                            return json.loads(item["text"])
                        except:
                            return {"raw": item["text"]}
            
            return result
            
        except Exception as e:
            return {"error": str(e)}

    
    async def search_logs_by_location(self, location: str, time_range: str = "24h", limit: int = 100) -> dict:
        """Search by location"""
        return await self.search_logs_by_country(location, time_range, limit)
    
    async def search_logs_by_ip(self, ip_address: str, time_range: str = "24h", limit: int = 100) -> dict:
        """Search by IP"""
        try:
            await self._call_server_simple({
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            })
            
            response = await self._call_server_simple({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "search_logs_by_ip",
                    "arguments": {
                        "ip_address": ip_address,
                        "time_range": time_range,
                        "limit": limit
                    }
                }
            })
            
            if "error" in response:
                return {"error": response["error"]}
            
            result = response.get("result", {})
            if "content" in result:
                for item in result["content"]:
                    if item.get("type") == "text":
                        try:
                            return json.loads(item["text"])
                        except:
                            return {"raw": item["text"]}
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        """Dummy close"""
        pass
