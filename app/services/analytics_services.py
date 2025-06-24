import os
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        # Get countries from environment variable
        countries_env = os.getenv("ANALYTICS_COUNTRIES", "IR,UA,BH,CY,EG,IQ,JO,KW,LB,OM,PS,QA,SA,SY,TR,AE,YE")
        self.target_countries = [c.strip() for c in countries_env.split(",")]
    
    async def prepare_comprehensive_analysis(self, mcp_client) -> Dict[str, Any]:
        """Prepare comprehensive log analysis data"""
        
        # Get data from different time ranges and groupings
        current_data = await self._get_multi_dimensional_data(mcp_client, "1h")
        
        # Get specific countries data
        countries_data = await self._get_countries_data(mcp_client, "1h")
        
        # NEW: Get IP analytics data
        ip_analytics = await self._get_ip_analytics(mcp_client, "1h")
        
        # Combine and analyze
        analysis_data = {
            "timestamp": datetime.now().isoformat(),
            "current_period": {
                **current_data,
                "ip_analytics": ip_analytics  # Add IP analytics here
            },
            "countries_analysis": countries_data,
            "summary_statistics": self._calculate_summary_stats(current_data, ip_analytics),  # Pass IP data
            "target_countries": self.target_countries
        }
        
        return analysis_data
    
    async def _get_ip_analytics(self, mcp_client, time_range: str) -> Dict[str, Any]:
        """Get comprehensive IP analytics using search_logs_by_ip with full range"""
        
        print(f"🔍 DEBUG: Getting IP analytics for {time_range} using IP range search")
        
        try:
            # Use the IP range 0.0.0.0/0 to get all IPs
            print("🔍 DEBUG: Searching logs with IP range 0.0.0.0/0 to get all IPs...")
            
            ip_logs_response = await mcp_client.search_logs_by_ip(
                ip_range="0.0.0.0/0",  # Get all IPs
                time_range=time_range,
                limit=5000  # Get more logs for better IP analysis
            )
            
            print(f"🔍 DEBUG: IP logs response type: {type(ip_logs_response)}")
            
            # Extract logs from response
            logs_data = []
            
            if isinstance(ip_logs_response, list):
                # Response is directly a list of logs
                logs_data = ip_logs_response
                print(f"🔍 DEBUG: Using response directly as list - {len(logs_data)} entries")
                
            elif isinstance(ip_logs_response, dict):
                print(f"🔍 DEBUG: Response is dict with keys: {list(ip_logs_response.keys())}")
                
                # Try common keys where logs might be stored
                possible_keys = ['logs', 'data', 'results', 'entries', 'records']
                
                for key in possible_keys:
                    if key in ip_logs_response:
                        potential_logs = ip_logs_response[key]
                        if isinstance(potential_logs, list):
                            logs_data = potential_logs
                            print(f"🔍 DEBUG: Found logs in key '{key}' - {len(logs_data)} entries")
                            break
                
                # If no logs found in common keys, check if there's an error
                if not logs_data and "error" in ip_logs_response:
                    print(f"❌ ERROR in response: {ip_logs_response['error']}")
                    return {
                        "ip_distribution": {},
                        "ip_by_country": {},
                        "ip_by_sensor": {},
                        "ip_by_city": {},
                        "total_unique_ips": 0,
                        "error": ip_logs_response['error']
                    }
                
                # If still no logs, print the full response for debugging
                if not logs_data:
                    print(f"🔍 DEBUG: Full response content: {ip_logs_response}")
                    
                    # Try to find any list in the response
                    for key, value in ip_logs_response.items():
                        if isinstance(value, list):
                            print(f"🔍 DEBUG: Found list in key '{key}' with {len(value)} items")
                            if len(value) > 0 and isinstance(value[0], dict):
                                print(f"🔍 DEBUG: First item in '{key}': {value[0]}")
                                logs_data = value
                                break
            
            print(f"🔍 DEBUG: Final logs_data length: {len(logs_data)}")
            
            # Debug: Check structure of first log if we have any
            if logs_data and len(logs_data) > 0:
                sample_log = logs_data[0]
                print(f"🔍 DEBUG: Sample log: {sample_log}")
                print(f"🔍 DEBUG: Sample log type: {type(sample_log)}")
                if isinstance(sample_log, dict):
                    print(f"🔍 DEBUG: Sample log keys: {list(sample_log.keys())}")
                else:
                    print(f"🔍 DEBUG: Sample log is not a dict: {sample_log}")
            else:
                print("⚠️ WARNING: No logs found to analyze")
                
                # Let's try a different approach - maybe the response format is different
                print(f"🔍 DEBUG: Trying to understand response format...")
                print(f"🔍 DEBUG: Response: {ip_logs_response}")
            
            # Analyze IP patterns
            ip_analytics = self._analyze_ip_addresses(logs_data)
            
            print(f"🔍 DEBUG: IP analytics completed - {ip_analytics.get('total_unique_ips', 0)} unique IPs found")
            
            return ip_analytics
            
        except Exception as e:
            print(f"❌ ERROR: Failed to get IP analytics: {e}")
            import traceback
            print(f"❌ ERROR: Traceback: {traceback.format_exc()}")
            logger.error(f"Failed to get IP analytics: {e}")
            return {
                "ip_distribution": {},
                "ip_by_country": {},
                "ip_by_sensor": {},
                "ip_by_city": {},
                "total_unique_ips": 0,
                "error": str(e)
            }
    
    async def _get_multi_dimensional_data(self, mcp_client, time_range: str) -> Dict[str, Any]:
        """Get data from multiple dimensions"""
        
        print(f"🔍 DEBUG: Getting multi-dimensional data for {time_range}")
        
        # Test the basic method first
        print("🔍 DEBUG: Testing basic get_traffic_analytics...")
        basic_test = await mcp_client.get_traffic_analytics(time_range, 1000)
        print(f"🔍 DEBUG: Basic test result: {type(basic_test)}")
        print(f"🔍 DEBUG: Basic test keys: {list(basic_test.keys()) if isinstance(basic_test, dict) else 'not dict'}")
        print(f"🔍 DEBUG: Basic test content: {basic_test}")
        
        # Get traffic analytics by different groupings
        print("🔍 DEBUG: Getting country analytics...")
        country_analytics = await mcp_client.get_traffic_analytics_by_group(
            group_by="country", time_range=time_range
        )
        print(f"🔍 DEBUG: Country analytics: {type(country_analytics)}")
        print(f"🔍 DEBUG: Country analytics keys: {list(country_analytics.keys()) if isinstance(country_analytics, dict) else 'not dict'}")
        
        print("🔍 DEBUG: Getting city analytics...")
        city_analytics = await mcp_client.get_traffic_analytics_by_group(
            group_by="city", time_range=time_range
        )
        print(f"🔍 DEBUG: City analytics: {type(city_analytics)}")
        
        print("🔍 DEBUG: Getting sensor analytics...")
        sensor_analytics = await mcp_client.get_traffic_analytics_by_group(
            group_by="sensor", time_range=time_range
        )
        print(f"🔍 DEBUG: Sensor analytics: {type(sensor_analytics)}")
        
        print("🔍 DEBUG: Getting ISP analytics...")
        isp_analytics = await mcp_client.get_traffic_analytics_by_group(
            group_by="isp", time_range=time_range
        )
        print(f"🔍 DEBUG: ISP analytics: {type(isp_analytics)}")
        
        result = {
            "country_analytics": country_analytics,
            "city_analytics": city_analytics,
            "sensor_analytics": sensor_analytics,
            "isp_analytics": isp_analytics,
            "time_range": time_range
        }
        
        print(f"🔍 DEBUG: Final result keys: {list(result.keys())}")
        return result

    
    async def _get_countries_data(self, mcp_client, time_range: str) -> Dict[str, Any]:
        """Get detailed data for specific countries"""
        
        countries_logs = await mcp_client.search_logs_by_countries(
            countries=self.target_countries, 
            time_range=time_range, 
            limit=5000
        )
        
        return {
            "target_countries": self.target_countries,
            "logs": countries_logs,
            "time_range": time_range
        }
    
    def _calculate_summary_stats(self, data: Dict[str, Any], ip_analytics: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate comprehensive summary statistics"""
        
        stats = {
            "total_requests": 0,
            "unique_countries": 0,
            "unique_cities": 0,
            "unique_sensors": 0,
            "unique_isps": 0,
            "unique_ips": 0,  # Add this
            "top_sensors": [],
            "top_countries": [],
            "top_cities": [],
            "top_isps": [],
            "top_ips": [],  # Add this
            "geographic_distribution": {},
            "risk_indicators": []
        }
        
        # Extract stats from different analytics
        for analytics_type in ["country_analytics", "city_analytics", "sensor_analytics", "isp_analytics"]:
            if analytics_type in data:
                analytics_data = data[analytics_type]
                if isinstance(analytics_data, dict):
                    # Extract relevant stats
                    if "total_requests" in analytics_data:
                        stats["total_requests"] = max(stats["total_requests"], analytics_data["total_requests"])
                    
                    if "unique_countries" in analytics_data:
                        stats["unique_countries"] = analytics_data["unique_countries"]
                    
                    if "unique_cities" in analytics_data:
                        stats["unique_cities"] = analytics_data["unique_cities"]
                    
                    if "unique_sensors" in analytics_data:
                        stats["unique_sensors"] = analytics_data["unique_sensors"]
                    
                    if "unique_isps" in analytics_data:
                        stats["unique_isps"] = analytics_data["unique_isps"]
                    
                    # Extract top items
                    group_type = analytics_type.replace("_analytics", "")
                    top_key = f"top_{group_type}"
                    if top_key in analytics_data:
                        stats[f"top_{group_type}s"] = analytics_data[top_key]
        
        # Add IP analytics stats
        if ip_analytics:
            stats["unique_ips"] = ip_analytics.get("total_unique_ips", 0)
            
            # Get top IPs
            ip_distribution = ip_analytics.get("ip_distribution", {})
            if ip_distribution:
                stats["top_ips"] = list(ip_distribution.items())[:10]  # Top 10 IPs
        
        return stats

        
    def _calculate_traffic_change(self, current: Dict, weekly: Dict) -> Dict[str, float]:
        """Calculate traffic change percentages"""
        # Simplified calculation - in real implementation, you'd do more sophisticated analysis
        return {
            "overall_change": 0.0,  # Placeholder
            "country_changes": {},
            "sensor_changes": {}
        }
    
    def _find_new_countries(self, current: Dict, weekly: Dict) -> List[str]:
        """Find countries that appear in current but not in weekly data"""
        # Placeholder implementation
        return []
    
    def _analyze_sensor_shifts(self, current: Dict, weekly: Dict) -> Dict[str, Any]:
        """Analyze changes in sensor usage"""
        return {"shifts": []}
    
    def _analyze_geographic_changes(self, current: Dict, weekly: Dict) -> Dict[str, Any]:
        """Analyze geographic distribution changes"""
        return {"changes": []}

    def _compare_periods(self, current_data: Dict[str, Any], previous_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compare current period data with previous period"""
        try:
            comparison = {
                "current_period": {
                    "total_requests": current_data.get("total_requests", 0),
                    "unique_countries": current_data.get("unique_countries", 0),
                    "unique_ips": current_data.get("unique_ips", 0)
                },
                "previous_period": {
                    "total_requests": previous_data.get("total_requests", 0),
                    "unique_countries": previous_data.get("unique_countries", 0),
                    "unique_ips": previous_data.get("unique_ips", 0)
                },
                "changes": {}
            }
            
            # Calculate percentage changes
            for metric in ["total_requests", "unique_countries", "unique_ips"]:
                current = comparison["current_period"][metric]
                previous = comparison["previous_period"][metric]
                
                if previous > 0:
                    change_pct = ((current - previous) / previous) * 100
                    comparison["changes"][metric] = {
                        "absolute": current - previous,
                        "percentage": round(change_pct, 2)
                    }
                else:
                    comparison["changes"][metric] = {
                        "absolute": current,
                        "percentage": "N/A" if current == 0 else "∞"
                    }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Period comparison failed: {e}")
            return {
                "current_period": current_data,
                "previous_period": previous_data,
                "changes": {},
                "error": str(e)
            }

    def _analyze_ip_addresses(self, logs_data: List[Dict]) -> Dict[str, Any]:
        """Analyze IP address patterns from logs"""
        from collections import Counter, defaultdict
        
        print(f"🔍 DEBUG: Analyzing {len(logs_data)} logs for IP patterns")
        
        if not logs_data:
            return {
                "ip_distribution": {},
                "ip_by_country": {},
                "ip_by_sensor": {},
                "ip_by_city": {},
                "total_unique_ips": 0
            }
        
        ip_counter = Counter()
        ip_by_country = defaultdict(lambda: {"unique_ips": set(), "requests": Counter()})
        ip_by_sensor = defaultdict(lambda: {"unique_ips": set(), "requests": Counter()})
        ip_by_city = defaultdict(lambda: {"unique_ips": set(), "requests": Counter()})
        
        for log_entry in logs_data:
            try:
                # Extract fields directly - we know the structure
                ip_address = log_entry.get('ip', 'Unknown')
                country = log_entry.get('country', 'Unknown')
                sensor = log_entry.get('sensor', 'Unknown')
                city = log_entry.get('city', 'Unknown')
                
                # Handle empty city
                if not city or city.strip() == '':
                    city = 'Unknown'
                
                # Count this IP
                ip_counter[ip_address] += 1
                
                # Group by country
                ip_by_country[country]["unique_ips"].add(ip_address)
                ip_by_country[country]["requests"][ip_address] += 1
                
                # Group by sensor
                ip_by_sensor[sensor]["unique_ips"].add(ip_address)
                ip_by_sensor[sensor]["requests"][ip_address] += 1
                
                # Group by city
                ip_by_city[city]["unique_ips"].add(ip_address)
                ip_by_city[city]["requests"][ip_address] += 1
                    
            except Exception as e:
                print(f"❌ ERROR: Failed to process log entry for IP analysis: {e}")
                continue
        
        print(f"🔍 DEBUG: IP counter results: {dict(ip_counter.most_common(5))}")
        
        # Convert to final format - FIXED VERSION
        def format_grouped_data(grouped_data):
            result = {}
            for group_name, data in grouped_data.items():
                unique_ips_count = len(data["unique_ips"])
                top_ip_data = data["requests"].most_common(1)
                
                if top_ip_data:
                    top_ip_address = top_ip_data[0][0]  # Get the IP address
                    top_ip_count = top_ip_data[0][1]    # Get the count
                    top_ip_info = f"{top_ip_address} ({top_ip_count})"
                else:
                    top_ip_info = "None"
                
                result[group_name] = {
                    "unique_ips": unique_ips_count,
                    "top_ip": top_ip_info,
                    "all_ips": dict(data["requests"].most_common())
                }
                
                # Debug output
                print(f"🔍 DEBUG: {group_name} - Unique IPs: {unique_ips_count}, Top IP: {top_ip_info}")
                
            return result
        
        # Build final result
        result = {
            "ip_distribution": dict(ip_counter.most_common()),
            "ip_by_country": format_grouped_data(ip_by_country),
            "ip_by_sensor": format_grouped_data(ip_by_sensor),
            "ip_by_city": format_grouped_data(ip_by_city),
            "total_unique_ips": len(set(ip_counter.keys()))
        }
        
        print(f"🔍 DEBUG: Final IP analysis result:")
        print(f"  - Total unique IPs: {result['total_unique_ips']}")
        print(f"  - Top 3 IPs: {list(result['ip_distribution'].items())[:3]}")
        
        return result
