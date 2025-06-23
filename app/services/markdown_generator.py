import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
from io import StringIO
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)

class MarkdownGenerator:
    def __init__(self):
        """Initialize the Markdown report generator"""
        # Set matplotlib style for better-looking charts
        plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
        sns.set_palette("husl")
        
        # Configure matplotlib for headless operation
        plt.ioff()  # Turn off interactive mode
        
        logger.info("📝 Markdown Generator initialized")
    
    async def generate_markdown_report(
        self, 
        analysis_data: Dict[str, Any], 
        nim_analysis: Dict[str, Any], 
        report_dir: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive Markdown report with charts
        """
        logger.info(f"📊 Generating Markdown report in: {report_dir}")
        
        try:
            # Validate and fix input data
            analysis_data = self._validate_and_fix_data(analysis_data, "analysis_data")
            nim_analysis = self._validate_and_fix_data(nim_analysis, "nim_analysis")
            
            logger.info(f"📊 Validated data - Analysis keys: {list(analysis_data.keys())}")
            logger.info(f"🤖 Validated data - NIM keys: {list(nim_analysis.keys())}")
            
            # Verify directory exists and is writable
            if not os.path.exists(report_dir):
                raise Exception(f"Report directory does not exist: {report_dir}")
            
            # Generate charts first (with individual error handling)
            image_files = []
            try:
                image_files = await self._generate_charts(analysis_data, report_dir)
                logger.info(f"📊 Generated {len(image_files)} charts successfully")
            except Exception as e:
                logger.warning(f"⚠️ Chart generation failed, continuing without charts: {e}")
                image_files = []
            
            # Generate the markdown content
            try:
                markdown_content = await self._generate_markdown_content(
                    analysis_data, nim_analysis, image_files
                )
                logger.info("📝 Markdown content generated successfully")
            except Exception as e:
                logger.error(f"❌ Failed to generate markdown content: {e}")
                # Generate minimal markdown content
                markdown_content = self._generate_minimal_markdown(analysis_data, nim_analysis)
                logger.info("📝 Generated minimal markdown content as fallback")
            
            # Save markdown file
            markdown_file = os.path.join(report_dir, "analysis_report.md")
            with open(markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # Save raw data as JSON for reference
            data_file = os.path.join(report_dir, "raw_data.json")
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'analysis_data': analysis_data,
                    'nim_analysis': nim_analysis,
                    'generated_at': datetime.now().isoformat()
                }, f, indent=2)
            
            logger.info(f"✅ Markdown report generated: {markdown_file}")
            logger.info(f"📊 Generated {len(image_files)} chart images")
            
            return {
                "markdown_file": markdown_file,
                "image_files": image_files,
                "data_file": data_file
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate Markdown report: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            raise

    def _validate_and_fix_data(self, data: Any, data_name: str) -> Dict[str, Any]:
        """Validate and fix data format issues"""
        logger.info(f"🔍 Validating {data_name}: type={type(data)}")
        
        # If it's already a dict, return as-is
        if isinstance(data, dict):
            return data
        
        # If it's a string, try to parse as JSON
        if isinstance(data, str):
            logger.warning(f"⚠️ {data_name} is a string, attempting to parse as JSON")
            try:
                parsed_data = json.loads(data)
                if isinstance(parsed_data, dict):
                    logger.info(f"✅ Successfully parsed {data_name} from JSON string")
                    return parsed_data
                else:
                    logger.warning(f"⚠️ Parsed {data_name} is not a dict: {type(parsed_data)}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Failed to parse {data_name} as JSON: {e}")
                logger.error(f"❌ String content preview: {str(data)[:200]}...")
        
        # If we get here, create a fallback structure
        logger.warning(f"⚠️ Creating fallback structure for {data_name}")
        
        if data_name == "analysis_data":
            return {
                "summary_statistics": {
                    "total_logs": 0,
                    "unique_ips": 0,
                    "total_bytes": 0
                },
                "country_analytics": {"analytics": []},
                "protocol_analytics": {"analytics": []},
                "raw_data": str(data)  # Store the original data for debugging
            }
        elif data_name == "nim_analysis":
            return {
                "executive_summary": f"Analysis data received in unexpected format: {type(data)}",
                "risk_level": "Unknown",
                "recommendations": ["Review data format issues", "Check MCP client response format"],
                "raw_data": str(data)  # Store the original data for debugging
            }
        else:
            return {"raw_data": str(data)}

    
    async def _generate_charts(self, analysis_data: Dict[str, Any], report_dir: str) -> List[str]:
        """Generate all charts and return list of image file paths"""
        image_files = []
        
        try:
            # Existing charts
            country_chart = await self._create_country_chart(analysis_data, report_dir)
            if country_chart:
                image_files.append(country_chart)
            
            sensor_chart = await self._create_protocol_chart(analysis_data, report_dir)
            if sensor_chart:
                image_files.append(sensor_chart)
            
            isp_chart = await self._create_isp_chart(analysis_data, report_dir)
            if isp_chart:
                image_files.append(isp_chart)
            
            # NEW: IP Analytics Charts
            ip_charts = await self._create_ip_charts(analysis_data, report_dir)
            image_files.extend(ip_charts)
            
            # Existing charts
            timeline_chart = await self._create_timeline_chart(analysis_data, report_dir)
            if timeline_chart:
                image_files.append(timeline_chart)
            
            summary_chart = await self._create_summary_chart(analysis_data, report_dir)
            if summary_chart:
                image_files.append(summary_chart)
                
        except Exception as e:
            logger.warning(f"⚠️ Error generating some charts: {e}")
        
        return image_files



    # Add this method to create IP charts
    async def _create_ip_charts(self, analysis_data: Dict[str, Any], report_dir: str) -> List[str]:
        """Create IP-related charts"""
        image_files = []
        
        try:
            current_period = analysis_data.get("current_period", {})
            ip_analytics = current_period.get("ip_analytics", {})
            
            if not ip_analytics:
                return image_files
            
            # 1. Top IPs Chart
            top_ips_chart = await self._create_top_ips_chart(ip_analytics, report_dir)
            if top_ips_chart:
                image_files.append(top_ips_chart)
            
            # 2. IPs by Country Chart
            ips_by_country_chart = await self._create_ips_by_country_chart(ip_analytics, report_dir)
            if ips_by_country_chart:
                image_files.append(ips_by_country_chart)
            
            # 3. IPs by Sensor Chart
            ips_by_sensor_chart = await self._create_ips_by_sensor_chart(ip_analytics, report_dir)
            if ips_by_sensor_chart:
                image_files.append(ips_by_sensor_chart)
                
        except Exception as e:
            logger.warning(f"⚠️ Error generating IP charts: {e}")
        
        return image_files

    async def _create_top_ips_chart(self, ip_analytics: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create top IPs bar chart"""
        try:
            ip_distribution = ip_analytics.get("ip_distribution", {})
            if not ip_distribution:
                return None
            
            # Take top 15 IPs
            top_ips = list(ip_distribution.items())[:15]
            ips = [item[0] for item in top_ips]
            requests = [item[1] for item in top_ips]
            
            plt.figure(figsize=(14, 8))
            bars = plt.barh(ips, requests, color=sns.color_palette("viridis", len(ips)))
            
            plt.title('Top 15 IP Addresses by Request Volume', fontsize=16, fontweight='bold')
            plt.xlabel('Total Requests', fontsize=12)
            plt.ylabel('IP Address', fontsize=12)
            
            # Add value labels
            for bar, value in zip(bars, requests):
                plt.text(bar.get_width() + max(requests)*0.01, bar.get_y() + bar.get_height()/2,
                        f'{value:,}', ha='left', va='center', fontweight='bold')
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "top_ips_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 Top IPs chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create top IPs chart: {e}")
            plt.close()
            return None

    async def _create_ips_by_country_chart(self, ip_analytics: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create IPs by country distribution chart"""
        try:
            ip_by_country = ip_analytics.get("ip_by_country", {})
            if not ip_by_country:
                return None
            
            # Count unique IPs per country
            country_ip_counts = {country: len(ips) for country, ips in ip_by_country.items()}
            sorted_countries = sorted(country_ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            countries = [item[0] for item in sorted_countries]
            ip_counts = [item[1] for item in sorted_countries]
            
            plt.figure(figsize=(12, 8))
            bars = plt.bar(countries, ip_counts, color=sns.color_palette("plasma", len(countries)))
            
            plt.title('Unique IP Addresses by Country (Top 10)', fontsize=16, fontweight='bold')
            plt.xlabel('Country', fontsize=12)
            plt.ylabel('Unique IP Addresses', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels
            for bar, value in zip(bars, ip_counts):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(ip_counts)*0.01,
                        f'{value}', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "ips_by_country_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 IPs by country chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create IPs by country chart: {e}")
            plt.close()
            return None

    async def _create_ips_by_sensor_chart(self, ip_analytics: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create IPs by sensor pie chart"""
        try:
            ip_by_sensor = ip_analytics.get("ip_by_sensor", {})
            if not ip_by_sensor:
                return None
            
            # Count unique IPs per sensor
            sensor_ip_counts = {sensor: len(ips) for sensor, ips in ip_by_sensor.items()}
            
            sensors = list(sensor_ip_counts.keys())
            ip_counts = list(sensor_ip_counts.values())
            
            plt.figure(figsize=(10, 8))
            colors = sns.color_palette("Set3", len(sensors))
            
            wedges, texts, autotexts = plt.pie(ip_counts, labels=sensors, autopct='%1.1f%%', 
                                            colors=colors, startangle=90)
            
            plt.title('Unique IP Distribution by Sensor', fontsize=16, fontweight='bold')
            
            # Enhance text appearance
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            plt.axis('equal')
            
            chart_path = os.path.join(report_dir, "ips_by_sensor_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 IPs by sensor chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create IPs by sensor chart: {e}")
            plt.close()
            return None

    
    async def _create_country_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create country traffic distribution chart"""
        try:
            # FIX: Get data from correct structure
            current_period = analysis_data.get("current_period", {})
            country_analytics = current_period.get("country_analytics", {})
            country_distribution = country_analytics.get("country_distribution", {})
            
            if not country_distribution:
                return None
            
            # Sort and take top 10
            sorted_countries = sorted(country_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
            
            countries = [item[0] for item in sorted_countries]
            requests = [item[1] for item in sorted_countries]
            
            plt.figure(figsize=(12, 8))
            bars = plt.bar(countries, requests, color=sns.color_palette("husl", len(countries)))
            
            plt.title('Top 10 Countries by Request Volume', fontsize=16, fontweight='bold')
            plt.xlabel('Country', fontsize=12)
            plt.ylabel('Total Requests', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels on bars
            for bar, value in zip(bars, requests):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(requests)*0.01,
                        f'{value:,}', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "country_traffic_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 Country chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create country chart: {e}")
            plt.close()
            return None
    
    async def _create_protocol_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create sensor usage pie chart"""
        try:
            # FIX: Get sensor data from correct structure
            current_period = analysis_data.get("current_period", {})
            sensor_analytics = current_period.get("sensor_analytics", {})
            sensor_distribution = sensor_analytics.get("sensor_distribution", {})
            
            if not sensor_distribution:
                return None
            
            sensors = list(sensor_distribution.keys())
            requests = list(sensor_distribution.values())
            
            plt.figure(figsize=(10, 8))
            colors = sns.color_palette("husl", len(sensors))
            
            wedges, texts, autotexts = plt.pie(requests, labels=sensors, autopct='%1.1f%%', 
                                            colors=colors, startangle=90)
            
            plt.title('Traffic Distribution by Sensor', fontsize=16, fontweight='bold')
            
            # Enhance text appearance
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            plt.axis('equal')
            
            chart_path = os.path.join(report_dir, "sensor_usage_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 Sensor chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create sensor chart: {e}")
            plt.close()
            return None

    
    async def _create_timeline_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create traffic timeline chart if time-series data is available"""
        try:
            # Check if we have time-series data
            time_series = analysis_data.get("time_series", [])
            if not time_series:
                logger.info("ℹ️ No time-series data available for timeline chart")
                return None
            
            # Convert to pandas DataFrame for easier handling
            df = pd.DataFrame(time_series)
            if 'timestamp' not in df.columns or 'requests' not in df.columns:
                return None
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            plt.figure(figsize=(14, 6))
            plt.plot(df['timestamp'], df['requests'], linewidth=2, color='#2E86AB', marker='o', markersize=4)
            
            plt.title('Traffic Timeline (Last 24 Hours)', fontsize=16, fontweight='bold')
            plt.xlabel('Time', fontsize=12)
            plt.ylabel('Requests per Hour', fontsize=12)
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.xticks(rotation=45)
            
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "traffic_timeline_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 Timeline chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create timeline chart: {e}")
            plt.close()
            return None
    
    async def _create_summary_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create summary statistics chart"""
        try:
            # FIX: Get stats from correct structure
            stats = analysis_data.get("summary_statistics", {})
            current_period = analysis_data.get("current_period", {})
            
            if not stats:
                return None
            
            # Prepare data for summary chart using correct field names
            metrics = []
            values = []
            
            if stats.get("total_requests"):
                metrics.append("Total Requests")
                values.append(stats["total_requests"])
            
            if stats.get("unique_countries"):
                metrics.append("Countries")
                values.append(stats["unique_countries"])

            if stats.get("unique_cities"):
                metrics.append("Cities")
                values.append(stats["unique_cities"])      

            if stats.get("unique_ips"):
                metrics.append("IPs")
                values.append(stats["unique_ips"])                            
            
            if stats.get("unique_sensors"):
                metrics.append("Sensors")
                values.append(stats["unique_sensors"])
                
            if stats.get("unique_isps"):
                metrics.append("ISPs")
                values.append(stats["unique_isps"])
        
            
            if not metrics:
                return None
            
            plt.figure(figsize=(12, 6))
            bars = plt.bar(metrics, values, color=sns.color_palette("viridis", len(metrics)))
            
            plt.title('Analysis Summary Statistics', fontsize=16, fontweight='bold')
            plt.ylabel('Count / Volume', fontsize=12)
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                if value >= 1000000:
                    label = f'{value/1000000:.1f}M'
                elif value >= 1000:
                    label = f'{value/1000:.1f}K'
                else:
                    label = f'{value:.0f}'
                
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.01,
                        label, ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "summary_statistics_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 Summary chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create summary chart: {e}")
            plt.close()
            return None

    async def _create_isp_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create ISP distribution chart"""
        try:
            current_period = analysis_data.get("current_period", {})
            isp_analytics = current_period.get("isp_analytics", {})
            isp_distribution = isp_analytics.get("isp_distribution", {})
            
            if not isp_distribution:
                return None
            
            # Sort and take top 10
            sorted_isps = sorted(isp_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
            
            isps = [item[0] for item in sorted_isps]
            requests = [item[1] for item in sorted_isps]
            
            plt.figure(figsize=(14, 8))
            bars = plt.barh(isps, requests, color=sns.color_palette("plasma", len(isps)))
            
            plt.title('Top 10 ISPs by Request Volume', fontsize=16, fontweight='bold')
            plt.xlabel('Total Requests', fontsize=12)
            plt.ylabel('ISP', fontsize=12)
            
            # Add value labels on bars
            for bar, value in zip(bars, requests):
                plt.text(bar.get_width() + max(requests)*0.01, bar.get_y() + bar.get_height()/2,
                        f'{value:,}', ha='left', va='center', fontweight='bold')
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "isp_distribution_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 ISP chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create ISP chart: {e}")
            plt.close()
            return None

    
    async def _generate_markdown_content(
        self, 
        analysis_data: Dict[str, Any], 
        nim_analysis: Dict[str, Any], 
        image_files: List[str]
    ) -> str:
        """Generate the complete Markdown content"""
        
        # Get base filenames for images (for markdown links)
        image_names = [os.path.basename(img) for img in image_files]
        
        # Start building markdown content
        md_content = StringIO()
        
        # EXTRACT DATA FROM CORRECT STRUCTURE
        stats = analysis_data.get("summary_statistics", {})
        current_period = analysis_data.get("current_period", {})
        
        # Get actual data from your structure
        country_analytics = current_period.get("country_analytics", {})
        country_distribution = country_analytics.get("country_distribution", {})
        
        sensor_analytics = current_period.get("sensor_analytics", {})
        sensor_distribution = sensor_analytics.get("sensor_distribution", {})
        
        isp_analytics = current_period.get("isp_analytics", {})
        isp_distribution = isp_analytics.get("isp_distribution", {})
        
        # Header
        md_content.write(f"# Oracle Cloud Infrastructure Log Analysis Report\n\n")
        md_content.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        md_content.write(f"**Analysis Period:** {current_period.get('time_range', '24 hours')}\n\n")
        
        # Table of Contents
        md_content.write("## Table of Contents\n\n")
        md_content.write("1. [Executive Summary](#executive-summary)\n")
        md_content.write("2. [Key Metrics](#key-metrics)\n")
        md_content.write("3. [Visual Analytics](#visual-analytics)\n")
        md_content.write("4. [Geographic Analysis](#geographic-analysis)\n")
        md_content.write("5. [Protocol Analysis](#protocol-analysis)\n")
        md_content.write("6. [Security Assessment](#security-assessment)\n")
        md_content.write("7. [Recommendations](#recommendations)\n")
        md_content.write("8. [Detailed Data](#detailed-data)\n\n")
        
        # Executive Summary
        md_content.write("## Executive Summary\n\n")
        if isinstance(nim_analysis.get("executive_summary"), str):
            md_content.write(f"{nim_analysis['executive_summary']}\n\n")
        else:
            total_logs = stats.get("total_requests", 0)
            md_content.write(f"This report analyzes {total_logs:,} log entries from Oracle Cloud Infrastructure. ")
            md_content.write("The analysis covers traffic patterns, geographic distribution, sensor usage, and security insights.\n\n")
        
        # Key Metrics - FIX THE FIELD NAMES
        md_content.write("## Key Metrics\n\n")
        
        md_content.write("| Metric | Value |\n")
        md_content.write("|--------|-------|\n")
        md_content.write(f"| Total Log Entries | {stats.get('total_requests', 0):,} |\n")
        md_content.write(f"| Unique IP Addresses | {stats.get('unique_ips', 'N/A')} |\n")
        md_content.write(f"| Countries Detected | {stats.get('unique_countries', 0)} |\n")
        md_content.write(f"| Cities Detected | {stats.get('unique_cities', 0)} |\n")
        md_content.write(f"| Sensors Used | {stats.get('unique_sensors', 0)} |\n")
        md_content.write(f"| ISPs Detected | {stats.get('unique_isps', 0)} |\n")
        md_content.write("\n")
        
        # Visual Analytics
        if image_names:
            md_content.write("## Visual Analytics\n\n")
            
            for image_name in image_names:
                if "country" in image_name.lower():
                    md_content.write("### Geographic Traffic Distribution\n\n")
                    md_content.write(f"![Country Traffic Chart]({image_name})\n\n")
                    
                elif "protocol" in image_name.lower():
                    md_content.write("### Protocol Usage Distribution\n\n")
                    md_content.write(f"![Protocol Usage Chart]({image_name})\n\n")
                    
                elif "timeline" in image_name.lower():
                    md_content.write("### Traffic Timeline\n\n")
                    md_content.write(f"![Traffic Timeline Chart]({image_name})\n\n")
                    
                elif "summary" in image_name.lower():
                    md_content.write("### Summary Statistics\n\n")
                    md_content.write(f"![Summary Statistics Chart]({image_name})\n\n")


        # IP Address Analysis (NEW SECTION)
        md_content.write("## IP Address Analysis\n\n")

        current_period = analysis_data.get("current_period", {})
        ip_analytics = current_period.get("ip_analytics", {})

        if ip_analytics:
            ip_distribution = ip_analytics.get("ip_distribution", {})
            ip_by_country = ip_analytics.get("ip_by_country", {})
            ip_by_sensor = ip_analytics.get("ip_by_sensor", {})
            ip_by_city = ip_analytics.get("ip_by_city", {})
            
            # Top IPs
            if ip_distribution:
                md_content.write("### Top IP Addresses by Request Volume\n\n")
                md_content.write("| Rank | IP Address | Requests | Percentage |\n")
                md_content.write("|------|------------|----------|------------|\n")
                
                total_requests = sum(ip_distribution.values())
                for i, (ip, requests) in enumerate(list(ip_distribution.items())[:15], 1):
                    percentage = (requests / total_requests * 100) if total_requests > 0 else 0
                    md_content.write(f"| {i} | {ip} | {requests:,} | {percentage:.1f}% |\n")
                md_content.write("\n")
            
            # IPs by Country
            if ip_by_country:
                md_content.write("### IP Distribution by Country\n\n")
                md_content.write("| Country | Unique IPs | Top IP (Requests) |\n")
                md_content.write("|---------|------------|-------------------|\n")
                
                for country, ips in list(ip_by_country.items())[:10]:
                    unique_count = len(ips)
                    top_ip = list(ips.items())[0] if ips else ("N/A", 0)
                    md_content.write(f"| {country} | {unique_count} | {top_ip[0]} ({top_ip[1]:,}) |\n")
                md_content.write("\n")
            
            # IPs by Sensor
            if ip_by_sensor:
                md_content.write("### IP Distribution by Sensor\n\n")
                md_content.write("| Sensor | Unique IPs | Top IP (Requests) |\n")
                md_content.write("|--------|------------|-------------------|\n")
                
                for sensor, ips in ip_by_sensor.items():
                    unique_count = len(ips)
                    top_ip = list(ips.items())[0] if ips else ("N/A", 0)
                    md_content.write(f"| {sensor} | {unique_count} | {top_ip[0]} ({top_ip[1]:,}) |\n")
                md_content.write("\n")
            
            # IPs by City (if available)
            if ip_by_city and len(ip_by_city) > 1:
                md_content.write("### IP Distribution by City (Top 10)\n\n")
                md_content.write("| City | Unique IPs | Top IP (Requests) |\n")
                md_content.write("|------|------------|-------------------|\n")
                
                # Sort cities by unique IP count
                sorted_cities = sorted(ip_by_city.items(), key=lambda x: len(x[1]), reverse=True)
                
                for city, ips in sorted_cities[:10]:
                    unique_count = len(ips)
                    top_ip = list(ips.items())[0] if ips else ("N/A", 0)
                    md_content.write(f"| {city} | {unique_count} | {top_ip[0]} ({top_ip[1]:,}) |\n")
                md_content.write("\n")

        else:
            md_content.write("No IP address data available in the current dataset.\n\n")

        
        # Geographic Analysis - FIX THE DATA SOURCE
        md_content.write("## Geographic Analysis\n\n")
        if country_distribution:
            md_content.write("### Top Countries by Request Volume\n\n")
            md_content.write("| Rank | Country | Requests | Percentage |\n")
            md_content.write("|------|---------|----------|------------|\n")
            
            total_requests = sum(country_distribution.values())
            sorted_countries = sorted(country_distribution.items(), key=lambda x: x[1], reverse=True)
            
            for i, (country, requests) in enumerate(sorted_countries[:10], 1):
                percentage = (requests / total_requests * 100) if total_requests > 0 else 0
                md_content.write(f"| {i} | {country} | {requests:,} | {percentage:.1f}% |\n")
            md_content.write("\n")
        else:
            md_content.write("No geographic data available in the current dataset.\n\n")
        
        # Sensor Analysis (instead of Protocol Analysis)
        md_content.write("## Sensor Analysis\n\n")
        if sensor_distribution:
            md_content.write("### Sensor Usage Breakdown\n\n")
            md_content.write("| Sensor | Requests | Percentage |\n")
            md_content.write("|--------|----------|------------|\n")
            
            total_requests = sum(sensor_distribution.values())
            sorted_sensors = sorted(sensor_distribution.items(), key=lambda x: x[1], reverse=True)
            
            for sensor, requests in sorted_sensors:
                percentage = (requests / total_requests * 100) if total_requests > 0 else 0
                md_content.write(f"| {sensor} | {requests:,} | {percentage:.1f}% |\n")
            md_content.write("\n")
        else:
            md_content.write("No sensor data available in the current dataset.\n\n")
        
        # ISP Analysis (NEW SECTION)
        md_content.write("## ISP Analysis\n\n")
        if isp_distribution:
            md_content.write("### Top ISPs by Request Volume\n\n")
            md_content.write("| Rank | ISP | Requests | Percentage |\n")
            md_content.write("|------|-----|----------|------------|\n")
            
            total_requests = sum(isp_distribution.values())
            sorted_isps = sorted(isp_distribution.items(), key=lambda x: x[1], reverse=True)
            
            for i, (isp, requests) in enumerate(sorted_isps[:10], 1):
                percentage = (requests / total_requests * 100) if total_requests > 0 else 0
                md_content.write(f"| {i} | {isp} | {requests:,} | {percentage:.1f}% |\n")
            md_content.write("\n")
        else:
            md_content.write("No ISP data available in the current dataset.\n\n")
        
        # Security Assessment
        md_content.write("## Security Assessment\n\n")
        if nim_analysis.get("security_analysis"):
            md_content.write(f"{nim_analysis['security_analysis']}\n\n")
        
        # Risk Level
        risk_level = nim_analysis.get("risk_level", "Unknown")
        risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}.get(risk_level, "⚪")
        md_content.write(f"**Risk Level:** {risk_emoji} {risk_level}\n\n")
        
        # Key Findings
        if nim_analysis.get("key_findings"):
            md_content.write("### Key Security Findings\n\n")
            findings = nim_analysis["key_findings"]
            if isinstance(findings, list):
                for finding in findings:
                    md_content.write(f"- {finding}\n")
            else:
                md_content.write(f"{findings}\n")
            md_content.write("\n")
        
        # Recommendations
        md_content.write("## Recommendations\n\n")
        if nim_analysis.get("recommendations"):
            recommendations = nim_analysis["recommendations"]
            if isinstance(recommendations, list):
                for i, rec in enumerate(recommendations, 1):
                    md_content.write(f"{i}. {rec}\n")
            else:
                md_content.write(f"{recommendations}\n")
            md_content.write("\n")
        else:
            md_content.write("- Continue monitoring traffic patterns for anomalies\n")
            md_content.write("- Review access logs regularly for security threats\n")
            md_content.write("- Implement automated alerting for unusual traffic spikes\n")
            md_content.write("- Consider geographic access controls based on traffic patterns\n\n")
        
        # Next Steps
        if nim_analysis.get("next_steps"):
            md_content.write("### Next Steps\n\n")
            next_steps = nim_analysis["next_steps"]
            if isinstance(next_steps, list):
                for step in next_steps:
                    md_content.write(f"- {step}\n")
            else:
                md_content.write(f"{next_steps}\n")
            md_content.write("\n")
        
        # Detailed Data Section
        md_content.write("## Detailed Data\n\n")
        md_content.write("### Analysis Metadata\n\n")
        md_content.write(f"- **Analysis Method:** {nim_analysis.get('analysis_method', 'Standard Analysis')}\n")
        md_content.write(f"- **Confidence Level:** {nim_analysis.get('confidence', 'Medium')}\n")
        md_content.write(f"- **Data Time Range:** {analysis_data.get('time_range', '24 hours')}\n")
        md_content.write(f"- **Report Generated:** {datetime.now().isoformat()}\n\n")
        
        # Footer
        md_content.write("---\n\n")
        md_content.write("*This report was automatically generated by the Oracle Cloud Infrastructure Log Analysis System.*\n")
        md_content.write("*For questions or additional analysis, please contact your system administrator.*\n")
        
        return md_content.getvalue()
