import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Tuple
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
    
    async def analyze_logs(self, logs_data: Dict[str, Any], analysis_prompt: str) -> Dict[str, Any]:
        """Analyze logs using NVIDIA NIM and parse the comprehensive response"""
        
        # Prepare the context with logs data
        logs_summary = self._prepare_logs_summary(logs_data)
        
        # Construct the full prompt - allow NIM to respond naturally
        full_prompt = f"""
{analysis_prompt}

LOGS DATA TO ANALYZE:
{logs_summary}

Please provide a comprehensive analysis including:
1. Executive summary and risk assessment
2. Key findings and security insights
3. Traffic patterns and anomalies
4. Specific recommendations and next steps
5. Data suitable for visualization (charts, graphs)

You may format your response in any clear, structured way. Include both JSON data and additional explanatory text as needed.
"""
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert cybersecurity analyst specializing in network traffic analysis and threat detection. Provide comprehensive, actionable analysis."
                        },
                        {
                            "role": "user",
                            "content": full_prompt
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 6000
                }
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            print(f"🔍 NIM CONTENT LENGTH: {len(content) if content else 0}")
            print(f"🔍 NIM CONTENT (first 300 chars): '{content[:300] if content else 'None'}'")

            # Parse the comprehensive response
            parsed_response = self._parse_comprehensive_response(content)
            return parsed_response
            
        except Exception as e:
            print(f"❌ Error calling NVIDIA NIM: {e}")
            raise

    def _parse_comprehensive_response(self, content: str) -> Dict[str, Any]:
        """Parse the comprehensive NIM response containing JSON + additional content"""
        
        # Extract JSON from markdown code block
        json_data = self._extract_json_from_markdown(content)
        
        # Extract additional sections
        additional_content = self._extract_additional_content(content)
        
        # Combine into a comprehensive response
        comprehensive_response = {
            # Core analysis from JSON
            "executive_summary": json_data.get("executive_summary", "Analysis completed"),
            "risk_level": json_data.get("risk_level", "Medium"),
            "security_analysis": json_data.get("security_analysis", {}),
            "key_findings": json_data.get("key_findings", []),
            "recommendations": json_data.get("recommendations", []),
            "next_steps": json_data.get("next_steps", []),
            "confidence": json_data.get("confidence", "Medium"),
            "analysis_method": json_data.get("analysis_method", "NVIDIA NIM Analysis"),
            
            # Additional structured data
            "traffic_patterns": json_data.get("traffic_patterns", {}),
            "anomalies": json_data.get("anomalies", []),
            "visualization_data": json_data.get("visualization_data", {}),
            
            # Additional content from the response
            "additional_analysis": additional_content,
            
            # Metadata
            "response_type": "comprehensive",
            "has_json": bool(json_data),
            "has_additional_content": bool(additional_content),
            "raw_response_length": len(content)
        }
        
        return comprehensive_response

    def _extract_json_from_markdown(self, content: str) -> Dict[str, Any]:
        """Extract JSON from markdown code block"""
        try:
            # Look for JSON code block
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                
                # Clean up common JSON issues
                json_str = self._clean_json_string(json_str)
                
                parsed_json = json.loads(json_str)
                print(f"✅ Successfully extracted JSON ({len(json_str)} chars)")
                return parsed_json
            else:
                print("⚠️ No JSON code block found")
                return {}
                
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing failed: {e}")
            return {}
        except Exception as e:
            print(f"⚠️ JSON extraction failed: {e}")
            return {}

    def _clean_json_string(self, json_str: str) -> str:
        """Clean up common JSON formatting issues"""
        # Remove JavaScript-style comments
        json_str = re.sub(r'//.*?\n', '\n', json_str)
        
        # Fix trailing commas before closing brackets/braces
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Remove any remaining markdown artifacts
        json_str = json_str.strip()
        
        return json_str

    def _extract_additional_content(self, content: str) -> Dict[str, Any]:
        """Extract additional content sections beyond the JSON"""
        additional = {}
        
        try:
            # Split content by the JSON block
            parts = re.split(r'```json.*?```', content, flags=re.DOTALL)
            
            if len(parts) > 1:
                # Content before JSON (introduction)
                intro = parts[0].strip()
                if intro:
                    additional["introduction"] = intro
                
                # Content after JSON (additional analysis)
                outro = parts[1].strip() if len(parts) > 1 else ""
                if outro:
                    additional["extended_analysis"] = outro
                    
                    # Try to extract specific sections
                    sections = self._parse_additional_sections(outro)
                    additional.update(sections)
            
        except Exception as e:
            print(f"⚠️ Error extracting additional content: {e}")
        
        return additional

    def _parse_additional_sections(self, text: str) -> Dict[str, Any]:
        """Parse additional sections from the extended analysis"""
        sections = {}
        
        try:
            # Look for markdown headers and content
            header_pattern = r'#{1,4}\s*([^#\n]+)\n(.*?)(?=#{1,4}|\Z)'
            matches = re.findall(header_pattern, text, re.DOTALL)
            
            for header, content in matches:
                header_clean = header.strip().lower().replace(' ', '_')
                content_clean = content.strip()
                
                if content_clean:
                    # Try to parse lists
                    if '1.' in content_clean or '-' in content_clean:
                        items = re.findall(r'(?:^\d+\.|\-)\s*(.+)', content_clean, re.MULTILINE)
                        if items:
                            sections[header_clean] = items
                        else:
                            sections[header_clean] = content_clean
                    else:
                        sections[header_clean] = content_clean
                        
        except Exception as e:
            print(f"⚠️ Error parsing additional sections: {e}")
        
        return sections

    def _prepare_logs_summary(self, logs_data: Dict[str, Any]) -> str:
        """Prepare a summary of logs data for analysis"""
        
        if not logs_data:
            return "No logs data available"
        
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

    async def close(self):
        await self.client.aclose()
