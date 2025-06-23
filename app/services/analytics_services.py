import os
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        # Get countries from environment variable
        countries_env = os.getenv("ANALYTICS_COUNTRIES", "US,CN,RU,DE,GB,FR,JP,BR,IN,CA")
        self.target_countries = [c.strip() for c in countries_env.split(",")]
    
    async def prepare_comprehensive_analysis(self, mcp_client) -> Dict[str, Any]:
        """Prepare comprehensive log analysis data"""
        
        # Get data from different time ranges and groupings
        current_data = await self._get_multi_dimensional_data(mcp_client, "1h")
        # weekly_data = await self._get_multi_dimensional_data(mcp_client, "7d")
        
        # Get specific countries data
        countries_data = await self._get_countries_data(mcp_client, "1h")
        
        # Combine and analyze
        analysis_data = {
            "timestamp": datetime.now().isoformat(),
            "current_period": current_data,
            # "weekly_trend": weekly_data,
            "countries_analysis": countries_data,
            # "comparative_analysis": self._compare_periods(current_data, weekly_data),  # Now synchronous
            "summary_statistics": self._calculate_summary_stats(current_data),
            "target_countries": self.target_countries
        }
        
        return analysis_data
    
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
    
    def _calculate_summary_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive summary statistics"""
        
        stats = {
            "total_requests": 0,
            "unique_countries": 0,
            "unique_cities": 0,
            "unique_sensors": 0,
            "unique_isps": 0,
            "top_sensors": [],
            "top_countries": [],
            "top_cities": [],
            "top_isps": [],
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
