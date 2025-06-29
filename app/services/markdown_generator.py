import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for thread safety
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
from io import StringIO
import numpy as np
from app.config import settings


# Configure logging
logger = logging.getLogger(__name__)

class MarkdownGenerator:
    def __init__(self):
        """Initialize the Markdown report generator with Nord theme"""
        
        # Nord Color Palette
        self.NORD_COLORS = {
            # Polar Night
            'nord0': '#2E3440',
            'nord1': '#3B4252', 
            'nord2': '#434C5E',
            'nord3': '#4C566A',
            # Snow Storm
            'nord4': '#D8DEE9',
            'nord5': '#E5E9F0', 
            'nord6': '#ECEFF4',
            # Frost
            'nord7': '#8FBCBB',
            'nord8': '#88C0D0',
            'nord9': '#81A1C1',
            'nord10': '#5E81AC',
            # Aurora
            'nord11': '#BF616A',  # Red
            'nord12': '#D08770',  # Orange
            'nord13': '#EBCB8B',  # Yellow
            'nord14': '#A3BE8C',  # Green
            'nord15': '#B48EAD'   # Purple
        }
        
        # Nord color sequences for multi-series charts
        self.NORD_SEQUENCE = [
            self.NORD_COLORS['nord10'],  # Blue
            self.NORD_COLORS['nord14'],  # Green
            self.NORD_COLORS['nord11'],  # Red
            self.NORD_COLORS['nord13'],  # Yellow
            self.NORD_COLORS['nord12'],  # Orange
            self.NORD_COLORS['nord15'],  # Purple
            self.NORD_COLORS['nord8'],   # Light Blue
            self.NORD_COLORS['nord7'],   # Teal
        ]
        
        # Configure matplotlib with Nord theme
        self._setup_nord_theme()
        
        # Configure matplotlib for headless operation
        plt.ioff()  # Turn off interactive mode
        
        logger.info("📝 Markdown Generator initialized with Nord theme")
    
    def _setup_nord_theme(self):
        """Setup matplotlib with Nord theme"""
        # Set the color palette
        sns.set_palette(self.NORD_SEQUENCE)
        
        # Configure matplotlib rcParams for Nord theme
        plt.rcParams.update({
            # Figure settings
            'figure.facecolor': self.NORD_COLORS['nord6'],
            'axes.facecolor': 'white',
            
            # Text and fonts
            'text.color': self.NORD_COLORS['nord0'],
            'axes.labelcolor': self.NORD_COLORS['nord1'],
            'axes.titlecolor': self.NORD_COLORS['nord0'],
            'xtick.color': self.NORD_COLORS['nord2'],
            'ytick.color': self.NORD_COLORS['nord2'],
            'font.family': 'sans-serif',
            'font.sans-serif': ['Inter', 'DejaVu Sans', 'Arial', 'sans-serif'],
            'font.size': 10,
            'axes.titlesize': 14,
            'axes.labelsize': 11,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 10,
            
            # Grid and spines
            'axes.grid': True,
            'grid.color': self.NORD_COLORS['nord4'],
            'grid.alpha': 0.6,
            'grid.linewidth': 0.8,
            'axes.spines.left': True,
            'axes.spines.bottom': True,
            'axes.spines.top': False,
            'axes.spines.right': False,
            'axes.edgecolor': self.NORD_COLORS['nord3'],
            'axes.linewidth': 1,
            
            # Legend
            'legend.frameon': True,
            'legend.facecolor': 'white',
            'legend.edgecolor': self.NORD_COLORS['nord4'],
            'legend.framealpha': 0.95,
            
            # Other
            'axes.axisbelow': True,
        })
    
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
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for the report"""
        import socket
        import platform
        import os
        
        now = datetime.now()
        
        # Get physical hostname from environment variable
        physical_hostname = os.getenv('PHYSICAL_HOSTNAME')
        if not physical_hostname:
            # Fallback to container hostname if env var not set
            physical_hostname = socket.gethostname()
        
        return {
            'hostname': physical_hostname,  # Real physical server hostname
            'container_name': socket.gethostname(),  # Pod name for reference
            'platform': platform.system(),
            'timestamp': now.isoformat(),
            'timestamp_str': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'report_id': f"oci-analysis-{now.strftime('%Y%m%d-%H%M%S')}"
        }


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

    def _generate_minimal_markdown(self, analysis_data: Dict[str, Any], nim_analysis: Dict[str, Any]) -> str:
        """Generate minimal markdown content as fallback"""
        md_content = StringIO()
        
        md_content.write(f"# Oracle Cloud Infrastructure Log Analysis Report\n\n")
        md_content.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        md_content.write("## Status\n\n")
        md_content.write("⚠️ **Note:** This is a minimal report due to data processing issues.\n\n")
        
        # Basic stats if available
        stats = analysis_data.get("summary_statistics", {})
        if stats:
            md_content.write("## Available Statistics\n\n")
            for key, value in stats.items():
                md_content.write(f"- **{key.replace('_', ' ').title()}:** {value}\n")
            md_content.write("\n")
        
        # NIM analysis if available
        if nim_analysis.get("executive_summary"):
            md_content.write("## Analysis Summary\n\n")
            md_content.write(f"{nim_analysis['executive_summary']}\n\n")
        
        md_content.write("---\n\n")
        md_content.write("*Minimal report generated due to data processing issues.*\n")
        
        return md_content.getvalue()
    
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
            
            # IP Analytics Charts
            ip_charts = await self._create_ip_charts(analysis_data, report_dir)
            image_files.extend(ip_charts)
            
            # Timeline and summary charts
            timeline_chart = await self._create_timeline_chart(analysis_data, report_dir)
            if timeline_chart:
                image_files.append(timeline_chart)
            
            summary_chart = await self._create_summary_chart(analysis_data, report_dir)
            if summary_chart:
                image_files.append(summary_chart)
                
        except Exception as e:
            logger.warning(f"⚠️ Error generating some charts: {e}")
        
        return image_files

    async def _create_ip_charts(self, analysis_data: Dict[str, Any], report_dir: str) -> List[str]:
        """Create IP-related charts"""
        image_files = []
        
        try:
            current_period = analysis_data.get("current_period", {})
            ip_analytics = current_period.get("ip_analytics", {})
            
            if not ip_analytics:
                logger.info("ℹ️ No IP analytics data available for charts")
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
        """Create top IPs bar chart with Nord theme"""
        try:
            ip_distribution = ip_analytics.get("ip_distribution", {})
            if not ip_distribution:
                return None
            
            # Take top 15 IPs
            top_ips = list(ip_distribution.items())[:15]
            ips = [item[0] for item in top_ips]
            requests = [item[1] for item in top_ips]
            
            fig, ax = plt.subplots(figsize=(14, 8))
            fig.patch.set_facecolor(self.NORD_COLORS['nord6'])
            
            # Create gradient colors from Nord palette
            colors = [self.NORD_COLORS['nord10'] if i % 2 == 0 else self.NORD_COLORS['nord8'] 
                    for i in range(len(ips))]
            
            bars = ax.barh(ips, requests, color=colors, edgecolor=self.NORD_COLORS['nord1'], linewidth=0.5)
            
            ax.set_title('Top 15 IP Addresses by Request Volume', 
                        fontsize=16, fontweight='bold', color=self.NORD_COLORS['nord0'], pad=20)
            ax.set_xlabel('Total Requests', fontsize=12, color=self.NORD_COLORS['nord1'])
            ax.set_ylabel('IP Address', fontsize=12, color=self.NORD_COLORS['nord1'])
            
            # Add value labels with Nord colors
            for bar, value in zip(bars, requests):
                ax.text(bar.get_width() + max(requests)*0.01, bar.get_y() + bar.get_height()/2,
                    f'{value:,}', ha='left', va='center', fontweight='bold', 
                    color=self.NORD_COLORS['nord0'])
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "top_ips_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor=self.NORD_COLORS['nord6'])
            plt.close()
            
            logger.info(f"📊 Top IPs chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create top IPs chart: {e}")
            plt.close()
            return None

    async def _create_ips_by_country_chart(self, ip_analytics: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create IPs by country distribution chart with Nord theme"""
        try:
            ip_by_country = ip_analytics.get("ip_by_country", {})
            if not ip_by_country:
                return None
            
            # Handle both old and new data formats
            country_ip_counts = {}
            
            for country, data in ip_by_country.items():
                if isinstance(data, dict):
                    # New format: {"unique_ips": count, "top_ip": "x.x.x.x"}
                    country_ip_counts[country] = data.get("unique_ips", 0)
                elif isinstance(data, list):
                    # Old format: list of IPs
                    country_ip_counts[country] = len(data)
                else:
                    # Fallback
                    country_ip_counts[country] = 1
            
            sorted_countries = sorted(country_ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            countries = [item[0] for item in sorted_countries]
            ip_counts = [item[1] for item in sorted_countries]
            
            fig, ax = plt.subplots(figsize=(12, 8))
            fig.patch.set_facecolor(self.NORD_COLORS['nord6'])
            
            colors = [self.NORD_SEQUENCE[i % len(self.NORD_SEQUENCE)] for i in range(len(countries))]
            
            bars = ax.bar(countries, ip_counts, color=colors, 
                        edgecolor=self.NORD_COLORS['nord1'], linewidth=0.8)
            
            ax.set_title('Unique IP Addresses by Country (Top 10)', 
                        fontsize=16, fontweight='bold', color=self.NORD_COLORS['nord0'], pad=20)
            ax.set_xlabel('Country', fontsize=12, color=self.NORD_COLORS['nord1'])
            ax.set_ylabel('Unique IP Addresses', fontsize=12, color=self.NORD_COLORS['nord1'])
            
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels
            for bar, value in zip(bars, ip_counts):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(ip_counts)*0.01,
                    f'{value}', ha='center', va='bottom', fontweight='bold',
                    color=self.NORD_COLORS['nord0'])
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "ips_by_country_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor=self.NORD_COLORS['nord6'])
            plt.close()
            
            logger.info(f"📊 IPs by country chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create IPs by country chart: {e}")
            plt.close()
            return None

    async def _create_ips_by_sensor_chart(self, ip_analytics: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create IPs by sensor pie chart with Nord theme"""
        try:
            ip_by_sensor = ip_analytics.get("ip_by_sensor", {})
            if not ip_by_sensor:
                return None
            
            # Handle both old and new data formats
            sensor_ip_counts = {}
            
            for sensor, data in ip_by_sensor.items():
                if isinstance(data, dict):
                    # New format: {"unique_ips": count, "top_ip": "x.x.x.x"}
                    sensor_ip_counts[sensor] = data.get("unique_ips", 0)
                elif isinstance(data, list):
                    # Old format: list of IPs
                    sensor_ip_counts[sensor] = len(data)
                else:
                    # Fallback
                    sensor_ip_counts[sensor] = 1
            
            sensors = list(sensor_ip_counts.keys())
            ip_counts = list(sensor_ip_counts.values())
            
            fig, ax = plt.subplots(figsize=(10, 8))
            fig.patch.set_facecolor(self.NORD_COLORS['nord6'])
            
            colors = [self.NORD_SEQUENCE[i % len(self.NORD_SEQUENCE)] for i in range(len(sensors))]
            
            wedges, texts, autotexts = ax.pie(ip_counts, labels=sensors, autopct='%1.1f%%', 
                                            colors=colors, startangle=90,
                                            wedgeprops=dict(edgecolor=self.NORD_COLORS['nord6'], linewidth=2))
            
            ax.set_title('Unique IP Distribution by Sensor', 
                        fontsize=16, fontweight='bold', color=self.NORD_COLORS['nord0'], pad=20)
            
            # Enhance text appearance
            for text in texts:
                text.set_color(self.NORD_COLORS['nord1'])
                text.set_fontweight('bold')
            
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(10)
            
            plt.axis('equal')
            
            chart_path = os.path.join(report_dir, "ips_by_sensor_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor=self.NORD_COLORS['nord6'])
            plt.close()
            
            logger.info(f"📊 IPs by sensor chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create IPs by sensor chart: {e}")
            plt.close()
            return None

    async def _create_country_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create country traffic distribution chart with Nord theme"""
        try:
            current_period = analysis_data.get("current_period", {})
            country_analytics = current_period.get("country_analytics", {})
            country_distribution = country_analytics.get("country_distribution", {})
            
            if not country_distribution:
                return None
            
            # Sort and take top 10
            sorted_countries = sorted(country_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
            
            countries = [item[0] for item in sorted_countries]
            requests = [item[1] for item in sorted_countries]
            
            fig, ax = plt.subplots(figsize=(12, 8))
            fig.patch.set_facecolor(self.NORD_COLORS['nord6'])
            
            # Use Nord color sequence
            colors = [self.NORD_SEQUENCE[i % len(self.NORD_SEQUENCE)] for i in range(len(countries))]
            
            bars = ax.bar(countries, requests, color=colors, 
                        edgecolor=self.NORD_COLORS['nord1'], linewidth=0.8)
            
            ax.set_title('Top 10 Countries by Request Volume', 
                        fontsize=16, fontweight='bold', color=self.NORD_COLORS['nord0'], pad=20)
            ax.set_xlabel('Country', fontsize=12, color=self.NORD_COLORS['nord1'])
            ax.set_ylabel('Total Requests', fontsize=12, color=self.NORD_COLORS['nord1'])
            
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels on bars
            for bar, value in zip(bars, requests):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(requests)*0.01,
                    f'{value:,}', ha='center', va='bottom', fontweight='bold',
                    color=self.NORD_COLORS['nord0'])
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "country_traffic_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor=self.NORD_COLORS['nord6'])
            plt.close()
            
            logger.info(f"📊 Country chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create country chart: {e}")
            plt.close()
            return None

    async def _create_protocol_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create sensor usage pie chart with Nord theme"""
        try:
            current_period = analysis_data.get("current_period", {})
            sensor_analytics = current_period.get("sensor_analytics", {})
            sensor_distribution = sensor_analytics.get("sensor_distribution", {})
            
            if not sensor_distribution:
                return None
            
            sensors = list(sensor_distribution.keys())
            requests = list(sensor_distribution.values())
            
            fig, ax = plt.subplots(figsize=(10, 8))
            fig.patch.set_facecolor(self.NORD_COLORS['nord6'])
            
            # Use Nord colors for pie chart
            colors = [self.NORD_SEQUENCE[i % len(self.NORD_SEQUENCE)] for i in range(len(sensors))]
            
            wedges, texts, autotexts = ax.pie(requests, labels=sensors, autopct='%1.1f%%', 
                                            colors=colors, startangle=90,
                                            wedgeprops=dict(edgecolor=self.NORD_COLORS['nord6'], linewidth=2))
            
            ax.set_title('Traffic Distribution by Sensor', 
                        fontsize=16, fontweight='bold', color=self.NORD_COLORS['nord0'], pad=20)
            
            # Enhance text appearance with Nord colors
            for text in texts:
                text.set_color(self.NORD_COLORS['nord1'])
                text.set_fontweight('bold')
            
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(10)
            
            plt.axis('equal')
            
            chart_path = os.path.join(report_dir, "sensor_usage_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor=self.NORD_COLORS['nord6'])
            plt.close()
            
            logger.info(f"📊 Sensor chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create sensor chart: {e}")
            plt.close()
            return None

    async def _create_timeline_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create traffic timeline chart with Nord theme"""
        try:
            time_series = analysis_data.get("time_series", [])
            if not time_series:
                logger.info("ℹ️ No time-series data available for timeline chart")
                return None
            
            df = pd.DataFrame(time_series)
            if 'timestamp' not in df.columns or 'requests' not in df.columns:
                return None
            
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            fig, ax = plt.subplots(figsize=(14, 6))
            fig.patch.set_facecolor(self.NORD_COLORS['nord6'])
            
            # Plot line with Nord colors
            ax.plot(df['timestamp'], df['requests'], 
                linewidth=3, color=self.NORD_COLORS['nord10'], 
                marker='o', markersize=6, markerfacecolor=self.NORD_COLORS['nord10'],
                markeredgecolor='white', markeredgewidth=1.5)
            
            # Fill area under curve
            ax.fill_between(df['timestamp'], df['requests'], alpha=0.3, 
                        color=self.NORD_COLORS['nord8'])
            
            ax.set_title('Traffic Timeline (Last 24 Hours)', 
                        fontsize=16, fontweight='bold', color=self.NORD_COLORS['nord0'], pad=20)
            ax.set_xlabel('Time', fontsize=12, color=self.NORD_COLORS['nord1'])
            ax.set_ylabel('Requests per Hour', fontsize=12, color=self.NORD_COLORS['nord1'])
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "traffic_timeline_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor=self.NORD_COLORS['nord6'])
            plt.close()
            
            logger.info(f"📊 Timeline chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create timeline chart: {e}")
            plt.close()
            return None

    async def _create_summary_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create summary statistics chart with Nord theme"""
        try:
            stats = analysis_data.get("summary_statistics", {})
            
            if not stats:
                return None
            
            # Prepare data for summary chart
            metrics = []
            values = []
            
            metric_mapping = [
                ("total_requests", "Total Requests"),
                ("unique_countries", "Countries"),
                ("unique_cities", "Cities"),
                ("unique_ips", "IPs"),
                ("unique_sensors", "Sensors"),
                ("unique_isps", "ISPs")
            ]
            
            for key, label in metric_mapping:
                if stats.get(key):
                    metrics.append(label)
                    values.append(stats[key])
            
            if not metrics:
                return None
            
            fig, ax = plt.subplots(figsize=(12, 6))
            fig.patch.set_facecolor(self.NORD_COLORS['nord6'])
            
            # Use alternating Nord colors
            colors = [self.NORD_SEQUENCE[i % len(self.NORD_SEQUENCE)] for i in range(len(metrics))]
            
            bars = ax.bar(metrics, values, color=colors, 
                        edgecolor=self.NORD_COLORS['nord1'], linewidth=0.8)
            
            ax.set_title('Analysis Summary Statistics', 
                        fontsize=16, fontweight='bold', color=self.NORD_COLORS['nord0'], pad=20)
            ax.set_ylabel('Count / Volume', fontsize=12, color=self.NORD_COLORS['nord1'])
            
            plt.xticks(rotation=45, ha='right')
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                if value >= 1000000:
                    label = f'{value/1000000:.1f}M'
                elif value >= 1000:
                    label = f'{value/1000:.1f}K'
                else:
                    label = f'{value:.0f}'
                
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.01,
                    label, ha='center', va='bottom', fontweight='bold',
                    color=self.NORD_COLORS['nord0'])
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "summary_statistics_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor=self.NORD_COLORS['nord6'])
            plt.close()
            
            logger.info(f"📊 Summary chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create summary chart: {e}")
            plt.close()
            return None

    async def _create_isp_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create ISP distribution chart with Nord theme"""
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
            
            fig, ax = plt.subplots(figsize=(14, 8))
            fig.patch.set_facecolor(self.NORD_COLORS['nord6'])
            
            # Create gradient effect with Nord colors
            colors = []
            for i in range(len(isps)):
                if i < 3:  # Top 3 get special colors
                    colors.append(self.NORD_COLORS['nord10'])  # Blue
                elif i < 6:
                    colors.append(self.NORD_COLORS['nord14'])  # Green
                else:
                    colors.append(self.NORD_COLORS['nord8'])   # Light blue
            
            bars = ax.barh(isps, requests, color=colors, 
                        edgecolor=self.NORD_COLORS['nord1'], linewidth=0.5)
            
            ax.set_title('Top 10 ISPs by Request Volume', 
                        fontsize=16, fontweight='bold', color=self.NORD_COLORS['nord0'], pad=20)
            ax.set_xlabel('Total Requests', fontsize=12, color=self.NORD_COLORS['nord1'])
            ax.set_ylabel('ISP', fontsize=12, color=self.NORD_COLORS['nord1'])
            
            # Add value labels on bars
            for bar, value in zip(bars, requests):
                ax.text(bar.get_width() + max(requests)*0.01, bar.get_y() + bar.get_height()/2,
                    f'{value:,}', ha='left', va='center', fontweight='bold',
                    color=self.NORD_COLORS['nord0'])
            
            plt.tight_layout()
            
            chart_path = os.path.join(report_dir, "isp_distribution_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor=self.NORD_COLORS['nord6'])
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
        md_content.write("4. [IP Address Analysis](#ip-address-analysis)\n")
        md_content.write("5. [Geographic Analysis](#geographic-analysis)\n")
        md_content.write("6. [Sensor Analysis](#sensor-analysis)\n")
        md_content.write("7. [ISP Analysis](#isp-analysis)\n")
        md_content.write("8. [Security Assessment](#security-assessment)\n")
        md_content.write("9. [Recommendations](#recommendations)\n")
        md_content.write("10. [Detailed Data](#detailed-data)\n\n")
        
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
                    
                elif "sensor" in image_name.lower():
                    md_content.write("### Sensor Usage Distribution\n\n")
                    md_content.write(f"![Sensor Usage Chart]({image_name})\n\n")
                    
                elif "timeline" in image_name.lower():
                    md_content.write("### Traffic Timeline\n\n")
                    md_content.write(f"![Traffic Timeline Chart]({image_name})\n\n")
                    
                elif "summary" in image_name.lower():
                    md_content.write("### Summary Statistics\n\n")
                    md_content.write(f"![Summary Statistics Chart]({image_name})\n\n")
                    
                elif "isp" in image_name.lower():
                    md_content.write("### ISP Distribution\n\n")
                    md_content.write(f"![ISP Distribution Chart]({image_name})\n\n")
                    
                elif "top_ips" in image_name.lower():
                    md_content.write("### Top IP Addresses\n\n")
                    md_content.write(f"![Top IPs Chart]({image_name})\n\n")
                    
                elif "ips_by_country" in image_name.lower():
                    md_content.write("### IP Distribution by Country\n\n")
                    md_content.write(f"![IPs by Country Chart]({image_name})\n\n")
                    
                elif "ips_by_sensor" in image_name.lower():
                    md_content.write("### IP Distribution by Sensor\n\n")
                    md_content.write(f"![IPs by Sensor Chart]({image_name})\n\n")

        # IP Address Analysis (FIXED SECTION)
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
            
            # IPs by Country - FIXED VERSION
            if ip_by_country:
                md_content.write("### IP Distribution by Country\n\n")
                md_content.write("| Country | Unique IPs | Top IP (Requests) |\n")
                md_content.write("|---------|------------|-------------------|\n")
                
                # Sort by unique IPs count
                sorted_countries = []
                for country, data in ip_by_country.items():
                    if isinstance(data, dict):
                        unique_count = data.get("unique_ips", 0)
                        top_ip = data.get("top_ip", "N/A")
                    elif isinstance(data, list):
                        unique_count = len(data)
                        top_ip = data[0] if data else "N/A"
                    else:
                        unique_count = 1
                        top_ip = str(data)
                    
                    sorted_countries.append((country, unique_count, top_ip))
                
                sorted_countries.sort(key=lambda x: x[1], reverse=True)
                
                for country, unique_count, top_ip in sorted_countries[:10]:
                    md_content.write(f"| {country} | {unique_count} | {top_ip} |\n")
                md_content.write("\n")
            
            # IPs by Sensor - FIXED VERSION
            if ip_by_sensor:
                md_content.write("### IP Distribution by Sensor\n\n")
                md_content.write("| Sensor | Unique IPs | Top IP (Requests) |\n")
                md_content.write("|--------|------------|-------------------|\n")
                
                for sensor, data in ip_by_sensor.items():
                    if isinstance(data, dict):
                        unique_count = data.get("unique_ips", 0)
                        top_ip = data.get("top_ip", "N/A")
                    elif isinstance(data, list):
                        unique_count = len(data)
                        top_ip = data[0] if data else "N/A"
                    else:
                        unique_count = 1
                        top_ip = str(data)
                    
                    md_content.write(f"| {sensor} | {unique_count} | {top_ip} |\n")
                md_content.write("\n")
            
            # IPs by City - FIXED VERSION
            if ip_by_city and len(ip_by_city) > 1:
                md_content.write("### IP Distribution by City (Top 10)\n\n")
                md_content.write("| City | Unique IPs | Top IP (Requests) |\n")
                md_content.write("|------|------------|-------------------|\n")
                
                # Sort cities by unique IP count
                sorted_cities = []
                for city, data in ip_by_city.items():
                    if isinstance(data, dict):
                        unique_count = data.get("unique_ips", 0)
                        top_ip = data.get("top_ip", "N/A")
                    elif isinstance(data, list):
                        unique_count = len(data)
                        top_ip = data[0] if data else "N/A"
                    else:
                        unique_count = 1
                        top_ip = str(data)
                    
                    sorted_cities.append((city, unique_count, top_ip))
                
                sorted_cities.sort(key=lambda x: x[1], reverse=True)
                
                for city, unique_count, top_ip in sorted_cities[:10]:
                    md_content.write(f"| {city} | {unique_count} | {top_ip} |\n")
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
        md_content.write(f"- **NVIDIA Model:** {settings.NVIDIA_MODEL}\n")
        md_content.write(f"- **Confidence Level:** {nim_analysis.get('confidence', 'Medium')}\n")
        md_content.write(f"- **Data Time Range:** {analysis_data.get('time_range', '1 hour')}\n")
        md_content.write(f"- **Report Generated:** {datetime.now().isoformat()}\n\n")
        
        # Footer
        md_content.write("---\n\n")
        md_content.write("*This report was automatically generated by the Oracle Cloud Infrastructure Log Analysis System.*\n")
        md_content.write("*For questions or additional analysis, please contact your system administrator.*\n")
        
        return md_content.getvalue()
