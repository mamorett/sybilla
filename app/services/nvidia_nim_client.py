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
            timeout=120.0
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
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            print(f"Error calling NVIDIA NIM: {e}")
            raise
    
    def _prepare_logs_summary(self, logs_data: Dict[str, Any]) -> str:
        """Prepare a summary of logs data for analysis"""
        if not logs_data or "logs" not in logs_data:
            return "No logs data available"
        
        logs = logs_data["logs"]
        total_count = logs_data.get("total_count", len(logs))
        
        # Create summary statistics
        countries = {}
        ips = {}
        protocols = {}
        
        for log in logs[:1000]:  # Limit for prompt size
            # Count by country
            country = log.get("country", "Unknown")
            countries[country] = countries.get(country, 0) + 1
            
            # Count by IP
            ip = log.get("ip_address", "Unknown")
            ips[ip] = ips.get(ip, 0) + 1
            
            # Count by protocol
            protocol = log.get("protocol", "Unknown")
            protocols[protocol] = protocols.get(protocol, 0) + 1
        
        summary = f"""
LOGS SUMMARY:
Total logs: {total_count}
Sample size analyzed: {min(len(logs), 1000)}

TOP COUNTRIES:
{self._format_top_items(countries, 10)}

TOP IP ADDRESSES:
{self._format_top_items(ips, 10)}

PROTOCOLS:
{self._format_top_items(protocols, 5)}

SAMPLE LOG ENTRIES:
{self._format_sample_logs(logs[:5])}
"""
        return summary
    
    def _format_top_items(self, items_dict: Dict[str, int], limit: int) -> str:
        """Format top items for display"""
        sorted_items = sorted(items_dict.items(), key=lambda x: x[1], reverse=True)
        return "\n".join([f"  {item}: {count}" for item, count in sorted_items[:limit]])
    
    def _format_sample_logs(self, logs: List[Dict]) -> str:
        """Format sample logs for display"""
        formatted = []
        for log in logs:
            formatted.append(f"  - IP: {log.get('ip_address', 'N/A')}, Country: {log.get('country', 'N/A')}, Protocol: {log.get('protocol', 'N/A')}")
        return "\n".join(formatted)
    
    async def close(self):
        await self.client.aclose()
