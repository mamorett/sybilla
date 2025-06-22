import asyncio
import json
from typing import Dict, Any, List
import httpx
from app.config import settings

class MCPClient:
    def __init__(self):
        self.base_url = settings.MCP_SERVER_URL
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_logs_by_country(self, country: str = None, country_code: str = None, 
                                   time_range: str = "24h", limit: int = 10000) -> Dict[str, Any]:
        """Search logs by country"""
        payload = {
            "name": "search_logs_by_country",
            "arguments": {
                "country": country,
                "country_code": country_code,
                "time_range": time_range,
                "limit": limit
            }
        }
        return await self._call_tool(payload)
    
    async def search_logs_by_location(self, lat_min: float, lat_max: float, 
                                    lon_min: float, lon_max: float,
                                    time_range: str = "24h", limit: int = 10000) -> Dict[str, Any]:
        """Search logs by geographic bounds"""
        payload = {
            "name": "search_logs_by_location",
            "arguments": {
                "lat_min": lat_min,
                "lat_max": lat_max,
                "lon_min": lon_min,
                "lon_max": lon_max,
                "time_range": time_range,
                "limit": limit
            }
        }
        return await self._call_tool(payload)
    
    async def search_logs_by_ip(self, ip_address: str = None, ip_range: str = None,
                              time_range: str = "24h", limit: int = 10000) -> Dict[str, Any]:
        """Search logs by IP"""
        payload = {
            "name": "search_logs_by_ip",
            "arguments": {
                "ip_address": ip_address,
                "ip_range": ip_range,
                "time_range": time_range,
                "limit": limit
            }
        }
        return await self._call_tool(payload)
    
    async def get_traffic_analytics(self, time_range: str = "24h", 
                                  group_by: str = "country", limit: int = 10000) -> Dict[str, Any]:
        """Get traffic analytics"""
        payload = {
            "name": "get_traffic_analytics",
            "arguments": {
                "time_range": time_range,
                "group_by": group_by,
                "limit": limit
            }
        }
        return await self._call_tool(payload)
    
    async def _call_tool(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make API call to MCP server"""
        try:
            response = await self.client.post(f"{self.base_url}/call_tool", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error calling MCP tool: {e}")
            raise
    
    async def close(self):
        await self.client.aclose()
