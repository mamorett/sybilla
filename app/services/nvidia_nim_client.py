import asyncio
from typing import Dict, Any, List
import httpx
from app.config import settings

class NVIDIANIMClient:
    def __init__(self):
        self.api_key = settings.NVIDIA_NIM_API_KEY
        self.base_url = settings.NVIDIA_NIM_BASE_URL
        self.model = settings.NVIDIA_MODEL
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=240.0
        )
    
    async def analyze_logs(self, logs_data: Dict[str, Any], analysis_prompt: str) -> str:
        """Analyze logs using NVIDIA NIM"""
        
        # Prepare the context with logs data
        logs_summary = self._prepare_logs_summary(logs_data)
        
        # Construct the full prompt
        full_prompt = f"""
{analysis_prompt}

LOGS DATA TO ANALYZE:
{logs_summary}

Please provide a comprehensive analysis including:
1. Key findings and patterns
2. Security insights
3. Traffic patterns
4. Anomalies or concerns
5. Recommendations
6. Data for visualization (provide specific metrics for charts)

Format your response as structured JSON with the following sections:
- executive_summary
- key_findings
- security_analysis
- traffic_patterns
- anomalies
- recommendations
- visualization_data (include data for charts/graphs)
"""
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert cybersecurity analyst specializing in network traffic analysis and threat detection."
                        },
                        {
                            "role": "user",
                            "content": full_prompt
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4000
                }
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"🔍 NIM API RESPONSE STATUS: {response.status_code}")
            print(f"🔍 NIM API RESPONSE KEYS: {list(result.keys())}")
            print(f"🔍 NIM API FULL RESPONSE: {result}")
            
            content = result["choices"][0]["message"]["content"]
            print(f"🔍 NIM CONTENT TYPE: {type(content)}")
            print(f"🔍 NIM CONTENT LENGTH: {len(content) if content else 0}")
            print(f"🔍 NIM CONTENT: '{content}'")

            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            print(f"Error calling NVIDIA NIM: {e}")
            raise
    
    
    def _format_top_items(self, items_dict: Dict[str, int], limit: int) -> str:
        """Format top items for display"""
        sorted_items = sorted(items_dict.items(), key=lambda x: x[1], reverse=True)
        return "\n".join([f"  {item}: {count}" for item, count in sorted_items[:limit]])
    
    def _format_sample_logs(self, logs: List[Dict]) -> str:
        """Format sample logs for display"""
        formatted = []
        for log in logs:
            formatted.append(f"  - IP: {log.get('ip_address', 'N/A')}, Country: {log.get('country', 'N/A')}, sensor: {log.get('sensor', 'N/A')}")
        return "\n".join(formatted)
    
    async def close(self):
        await self.client.aclose()

    def _prepare_logs_summary(self, logs_data: Dict[str, Any]) -> str:
        """Prepare a summary of logs data for analysis"""
        
        # DEBUG: Log what we actually received
        print(f"🔍 NIM CLIENT DEBUG: logs_data keys: {list(logs_data.keys())}")
        print(f"🔍 NIM CLIENT DEBUG: logs_data type: {type(logs_data)}")
        
        # Handle the actual structure from analytics service
        if not logs_data:
            return "No logs data available"
        
        # Extract data from the correct structure
        current_period = logs_data.get("current_period", {})
        summary_stats = logs_data.get("summary_statistics", {})
        
        # Get country data
        country_analytics = current_period.get("country_analytics", {})
        country_distribution = country_analytics.get("country_distribution", {})
        
        # Get sensor data
        sensor_analytics = current_period.get("sensor_analytics", {})
        sensor_distribution = sensor_analytics.get("sensor_distribution", {})
        
        # Get ISP data
        isp_analytics = current_period.get("isp_analytics", {})
        isp_distribution = isp_analytics.get("isp_distribution", {})
        
        summary = f"""
    LOGS ANALYSIS SUMMARY:
    Total requests: {summary_stats.get('total_requests', 0):,}
    Unique countries: {summary_stats.get('unique_countries', 0)}
    Unique sensors: {summary_stats.get('unique_sensors', 0)}
    Unique ISPs: {summary_stats.get('unique_isps', 0)}

    TOP COUNTRIES BY TRAFFIC:
    {self._format_distribution(country_distribution, 10)}

    SENSOR DISTRIBUTION:
    {self._format_distribution(sensor_distribution, 10)}

    TOP ISPs:
    {self._format_distribution(isp_distribution, 10)}

    TIME RANGE: {current_period.get('time_range', 'Unknown')}
    """
        return summary

    def _format_distribution(self, distribution: Dict[str, int], limit: int) -> str:
        """Format distribution data for display"""
        if not distribution:
            return "  No data available"
        
        sorted_items = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        return "\n".join([f"  {item}: {count:,}" for item, count in sorted_items[:limit]])
