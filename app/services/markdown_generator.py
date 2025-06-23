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
            # 1. Country Traffic Chart
            country_chart = await self._create_country_chart(analysis_data, report_dir)
            if country_chart:
                image_files.append(country_chart)
            
            # 2. Protocol Usage Chart
            protocol_chart = await self._create_protocol_chart(analysis_data, report_dir)
            if protocol_chart:
                image_files.append(protocol_chart)
            
            # 3. Traffic Timeline Chart (if time-series data available)
            timeline_chart = await self._create_timeline_chart(analysis_data, report_dir)
            if timeline_chart:
                image_files.append(timeline_chart)
            
            # 4. Summary Statistics Chart
            summary_chart = await self._create_summary_chart(analysis_data, report_dir)
            if summary_chart:
                image_files.append(summary_chart)
                
        except Exception as e:
            logger.warning(f"⚠️ Error generating some charts: {e}")
        
        return image_files
    
    async def _create_country_chart(self, analysis_data: Dict[str, Any], report_dir: str) -> Optional[str]:
        """Create country traffic distribution chart"""
        try:
            country_data = analysis_data.get("country_analytics", {}).get("analytics", [])
            if not country_data:
                return None
            
            # Take top 10 countries
            top_countries = country_data[:10]
            
            countries = [item["country"] for item in top_countries]
            requests = [item["total_requests"] for item in top_countries]
            
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
        """Create protocol usage pie chart"""
        try:
            protocol_data = analysis_data.get("protocol_analytics", {}).get("analytics", [])
            if not protocol_data:
                return None
            
            protocols = [item["protocol"] for item in protocol_data]
            requests = [item["total_requests"] for item in protocol_data]
            
            plt.figure(figsize=(10, 8))
            colors = sns.color_palette("husl", len(protocols))
            
            wedges, texts, autotexts = plt.pie(requests, labels=protocols, autopct='%1.1f%%', 
                                              colors=colors, startangle=90)
            
            plt.title('Traffic Distribution by Protocol', fontsize=16, fontweight='bold')
            
            # Enhance text appearance
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            plt.axis('equal')
            
            chart_path = os.path.join(report_dir, "protocol_usage_chart.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 Protocol chart saved: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create protocol chart: {e}")
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
            stats = analysis_data.get("summary_statistics", {})
            if not stats:
                return None
            
            # Prepare data for summary chart
            metrics = []
            values = []
            
            if stats.get("total_logs"):
                metrics.append("Total Logs")
                values.append(stats["total_logs"])
            
            if stats.get("unique_ips"):
                metrics.append("Unique IPs")
                values.append(stats["unique_ips"])
            
            if stats.get("total_bytes"):
                metrics.append("Total MB")
                values.append(stats["total_bytes"] / (1024 * 1024))
            
            country_count = len(analysis_data.get("country_analytics", {}).get("analytics", []))
            if country_count:
                metrics.append("Countries")
                values.append(country_count)
            
            protocol_count = len(analysis_data.get("protocol_analytics", {}).get("analytics", []))
            if protocol_count:
                metrics.append("Protocols")
                values.append(protocol_count)
            
            if not metrics:
                return None
            
            plt.figure(figsize=(10, 6))
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
        
        # Header
        md_content.write(f"# Oracle Cloud Infrastructure Log Analysis Report\n\n")
        md_content.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")
        md_content.write(f"**Analysis Period:** {analysis_data.get('time_range', '24 hours')}\n\n")
        
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
            stats = analysis_data.get("summary_statistics", {})
            total_logs = stats.get("total_logs", 0)
            md_content.write(f"This report analyzes {total_logs:,} log entries from Oracle Cloud Infrastructure. ")
            md_content.write("The analysis covers traffic patterns, geographic distribution, protocol usage, and security insights.\n\n")
        
        # Key Metrics
        md_content.write("## Key Metrics\n\n")
        stats = analysis_data.get("summary_statistics", {})
        
        md_content.write("| Metric | Value |\n")
        md_content.write("|--------|-------|\n")
        md_content.write(f"| Total Log Entries | {stats.get('total_logs', 0):,} |\n")
        md_content.write(f"| Unique IP Addresses | {stats.get('unique_ips', 0):,} |\n")
        md_content.write(f"| Total Data Volume | {stats.get('total_bytes', 0) / (1024*1024):.1f} MB |\n")
        md_content.write(f"| Countries Detected | {len(analysis_data.get('country_analytics', {}).get('analytics', []))} |\n")
        md_content.write(f"| Protocols Used | {len(analysis_data.get('protocol_analytics', {}).get('analytics', []))} |\n")
        
        if stats.get('total_logs', 0) > 0:
            avg_bytes = stats.get('total_bytes', 0) / stats.get('total_logs', 1)
            md_content.write(f"| Average Request Size | {avg_bytes:.0f} bytes |\n")
        
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
        
        # Geographic Analysis
        md_content.write("## Geographic Analysis\n\n")
        country_data = analysis_data.get("country_analytics", {}).get("analytics", [])
        if country_data:
            md_content.write("### Top Countries by Request Volume\n\n")
            md_content.write("| Rank | Country | Requests | Percentage |\n")
            md_content.write("|------|---------|----------|------------|\n")
            
            total_requests = sum(item["total_requests"] for item in country_data)
            for i, country in enumerate(country_data[:10], 1):
                percentage = (country["total_requests"] / total_requests * 100) if total_requests > 0 else 0
                md_content.write(f"| {i} | {country['country']} | {country['total_requests']:,} | {percentage:.1f}% |\n")
            md_content.write("\n")
        else:
            md_content.write("No geographic data available in the current dataset.\n\n")
        
        # Protocol Analysis
        md_content.write("## Protocol Analysis\n\n")
        protocol_data = analysis_data.get("protocol_analytics", {}).get("analytics", [])
        if protocol_data:
            md_content.write("### Protocol Usage Breakdown\n\n")
            md_content.write("| Protocol | Requests | Data Volume (MB) |\n")
            md_content.write("|----------|----------|------------------|\n")
            
            for protocol in protocol_data:
                data_mb = protocol.get("total_bytes", 0) / (1024 * 1024)
                md_content.write(f"| {protocol['protocol']} | {protocol['total_requests']:,} | {data_mb:.1f} |\n")
            md_content.write("\n")
        else:
            md_content.write("No protocol data available in the current dataset.\n\n")
        
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
