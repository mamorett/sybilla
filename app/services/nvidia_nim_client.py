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
        """
        Analyze logs using NVIDIA NIM with the provided prompt.
        
        Args:
            logs_data: The log data (passed for context but prompt should be complete)
            analysis_prompt: Complete analysis prompt from scheduler
        
        Returns:
            Parsed comprehensive response from NIM
        """
        
        print(f"🔍 NIM CLIENT: Received prompt length: {len(analysis_prompt)} characters")
        print(f"🔍 NIM CLIENT: Using prompt from scheduler (no modification)")
        
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
                            "content": analysis_prompt  # Use ONLY the prompt from scheduler
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 6000
                }
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            print(f"🔍 NIM RESPONSE LENGTH: {len(content) if content else 0}")
            print(f"🔍 NIM RESPONSE (first 300 chars): '{content[:300] if content else 'None'}'")

            # Parse the comprehensive response
            parsed_response = self._parse_comprehensive_response(content)
            print(f"✅ NIM CLIENT: Parsed response with {len(parsed_response)} fields")
            
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
            # Core analysis from JSON (with fallbacks)
            "executive_summary": json_data.get("executive_summary", "Analysis completed"),
            "risk_level": json_data.get("risk_level", "Medium"),
            "security_analysis": json_data.get("security_analysis", "Security analysis completed"),
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
            "raw_response_length": len(content),
            "raw_response": content  # Keep full response for debugging
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

    async def close(self):
        await self.client.aclose()
