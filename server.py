# server.py - Fixed to handle both single and continuous requests
import asyncio
import json
import sys
import logging
from oracle_client import OracleLogsClient

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPServer:
    def __init__(self):
        self.oracle_client = OracleLogsClient()
        self.initialized = False
        
    async def handle_initialize(self, request):
        """Handle initialize request"""
        logger.info("📋 Handling initialize request")
        self.initialized = True
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "experimental": {}
                },
                "serverInfo": {
                    "name": "oracle-logs-mcp",
                    "version": "1.9.4"
                }
            }
        }
    
    async def handle_list_tools(self, request):
        """Handle tools/list request"""
        logger.info("📋 Handling list_tools request")
        
        if not self.initialized:
            logger.info("🔄 Auto-initializing server")
            self.initialized = True
        
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "tools": [
                    {
                        "name": "get_traffic_analytics",
                        "description": "Get comprehensive traffic analytics from Oracle logs with country, IP, and request statistics",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "time_range": {"type": "string", "default": "24h", "description": "Time range (e.g., '1h', '24h', '7d', '30d')"},
                                "group_by": {"type": "string", "default": "country", "description": "Group by: country, city, isp, sensor"},
                                "limit": {"type": "integer", "default": 1000, "description": "Maximum results"},
                                "max_results": {"type": "integer", "default": 1000, "description": "Maximum results to process"}
                            }
                        }
                    },
                    {
                        "name": "search_logs_by_country",
                        "description": "Search Oracle logs filtered by specific country",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "country": {"type": "string", "description": "Country name (e.g., 'United States', 'Germany')"},
                                "country_code": {"type": "string", "description": "Country code (e.g., 'US', 'DE')"},
                                "time_range": {"type": "string", "default": "24h"},
                                "limit": {"type": "integer", "default": 100},
                                "max_results": {"type": "integer", "default": 100}
                            }
                        }
                    },
                    {
                        "name": "search_logs_by_location",
                        "description": "Search Oracle logs by geographic coordinates",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "lat_min": {"type": "number", "description": "Minimum latitude"},
                                "lat_max": {"type": "number", "description": "Maximum latitude"},
                                "lon_min": {"type": "number", "description": "Minimum longitude"},
                                "lon_max": {"type": "number", "description": "Maximum longitude"},
                                "time_range": {"type": "string", "default": "24h"},
                                "limit": {"type": "integer", "default": 100},
                                "max_results": {"type": "integer", "default": 100}
                            },
                            "required": ["lat_min", "lat_max", "lon_min", "lon_max"]
                        }
                    },
                    {
                        "name": "search_logs_by_ip",
                        "description": "Search Oracle logs for specific IP address or range",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "ip_address": {"type": "string", "description": "Specific IP address"},
                                "ip_range": {"type": "string", "description": "IP range (e.g., '192.168.1.0/24')"},
                                "time_range": {"type": "string", "default": "24h"},
                                "limit": {"type": "integer", "default": 1000},
                                "max_results": {"type": "integer", "default": 1000}
                            }
                        }
                    }
                ]
            }
        }
    
    async def handle_call_tool(self, request):
        """Handle tools/call request"""
        if not self.initialized:
            logger.info("🔄 Auto-initializing server for tool call")
            self.initialized = True
        
        try:
            params = request["params"]
            name = params["name"]
            arguments = params.get("arguments", {})
            
            # ADD THIS DETAILED LOGGING
            logger.info(f"🔧 Executing tool: {name}")
            logger.info(f"📋 Full request: {json.dumps(request, indent=2)}")
            logger.info(f"📋 Arguments received: {json.dumps(arguments, indent=2)}")
            
            result = None
            
            if name == "get_traffic_analytics":
                logger.info(f"🔍 Calling oracle_client.get_traffic_analytics with: {arguments}")
                result = await self.oracle_client.get_traffic_analytics(arguments)
                logger.info(f"📊 Oracle client returned: {type(result)} with {len(result) if isinstance(result, (list, dict)) else 'unknown'} items")
                
            elif name == "search_logs_by_country":
                logger.info(f"🔍 Calling oracle_client.search_logs_by_country with: {arguments}")
                result = await self.oracle_client.search_logs_by_country(arguments)
                logger.info(f"📊 Oracle client returned: {type(result)} with {len(result) if isinstance(result, (list, dict)) else 'unknown'} items")

            elif name == "search_logs_by_location":
                result = await self.oracle_client.search_logs_by_location(arguments)
                        
            elif name == "search_logs_by_ip":
                result = await self.oracle_client.search_logs_by_ip(arguments)
                
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request["id"],
                    "error": {"code": -1, "message": f"Unknown tool: {name}"}
                }
            
            logger.info(f"✅ Tool {name} executed successfully")
            
            # Convert LogEntry objects to dictionaries if needed
            if isinstance(result, list) and result and hasattr(result[0], '__dict__'):
                result = [entry.__dict__ if hasattr(entry, '__dict__') else entry for entry in result]
            
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, default=str)
                        }
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Tool execution failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {"code": -1, "message": str(e)}
            }
    
    async def handle_request(self, request):
        """Route request to appropriate handler"""
        method = request.get("method")
        
        if method == "initialize":
            return await self.handle_initialize(request)
        elif method == "tools/list":
            return await self.handle_list_tools(request)
        elif method == "tools/call":
            return await self.handle_call_tool(request)
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }

async def main():
    """Main server loop - handles both single requests and continuous operation"""
    logger.info("🚀 Starting Oracle Logs MCP Server (Direct Protocol Implementation)")
    
    server = MCPServer()
    
    logger.info("💡 MCP Server ready for connections")
    logger.info("🔧 Available tools: get_traffic_analytics, search_logs_by_country, search_logs_by_location, search_logs_by_ip")
    
    try:
        # Check if we have input waiting (for single request mode)
        import select
        if select.select([sys.stdin], [], [], 0.1)[0]:
            # Single request mode - read all input at once
            input_data = sys.stdin.read().strip()
            if input_data:
                try:
                    request = json.loads(input_data)
                    logger.info(f"📨 Single request: {request.get('method', 'unknown')} (id: {request.get('id', 'none')})")
                    
                    response = await server.handle_request(request)
                    print(json.dumps(response), flush=True)
                    logger.info(f"📤 Sent response for request id: {response.get('id', 'none')}")
                    return
                    
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON received: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"}
                    }
                    print(json.dumps(error_response), flush=True)
                    return
        
        # Continuous mode - read line by line
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                logger.info(f"📨 Received request: {request.get('method', 'unknown')} (id: {request.get('id', 'none')})")
                
                response = await server.handle_request(request)
                print(json.dumps(response), flush=True)
                logger.info(f"📤 Sent response for request id: {response.get('id', 'none')}")
                
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON received: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }
                print(json.dumps(error_response), flush=True)
            
            except Exception as e:
                logger.error(f"❌ Request handling failed: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                }
                print(json.dumps(error_response), flush=True)
    
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
