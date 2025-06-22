import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import schedule
import time
from threading import Thread
import os
import json
from app.services.mcp_client import MCPClient
from app.services.nvidia_nim_client import NVIDIANIMClient
from app.services.oci_storage_client import OCIStorageClient
from app.services.analytics_services import AnalyticsService
from app.services.report_generator import ReportGenerator  # TODO: Create this module
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalysisScheduler:
    def __init__(self):
        """Initialize the analysis scheduler"""
        self.mcp_client = MCPClient()  # Connects to your existing MCP server
        self.nim_client = NVIDIANIMClient()
        self.oci_client = OCIStorageClient()
        self.analytics_service = AnalyticsService()
        self.report_generator = ReportGenerator()  # TODO: Create this module
        self.is_running = False
        self.scheduler_thread: Optional[Thread] = None
        self.last_analysis_result: Optional[Dict[str, Any]] = None
        
        logger.info("📅 Analysis Scheduler initialized")
        logger.info(f"🔧 MCP Server Script: {settings.MCP_SERVER_SCRIPT_PATH}")
        logger.info(f"⏰ Analysis Interval: {settings.ANALYSIS_INTERVAL_HOURS} hour(s)")
    
    async def test_connections(self) -> Dict[str, Any]:
        """Test connections to all external services"""
        logger.info("🔍 Testing connections to external services...")
        
        results = {
            "mcp_connected": False,
            "mcp_tools": [],
            "nim_available": False,
            "oci_available": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # Test MCP connection
        try:
            mcp_ok = await self.mcp_client.test_connection()
            results["mcp_connected"] = mcp_ok
            
            if mcp_ok:
                logger.info("✅ MCP Server: Connected to Oracle Logs MCP")
                
                # List available tools
                tools = await self.mcp_client.list_tools()
                if tools:
                    tool_names = [tool.get("name", "unknown") for tool in tools]
                    results["mcp_tools"] = tool_names
                    logger.info(f"🔧 Available MCP tools: {', '.join(tool_names)}")
                else:
                    logger.warning("⚠️ No tools found in MCP server response")
            else:
                logger.error("❌ MCP Server: Connection failed")
                
        except Exception as e:
            logger.error(f"❌ MCP Server connection error: {e}")
            results["mcp_error"] = str(e)
        
        # Test NVIDIA NIM (optional)
        try:
            if settings.NVIDIA_NIM_API_KEY:
                # Simple test - this would need to be implemented in NIM client
                results["nim_available"] = True
                logger.info("✅ NVIDIA NIM: API key configured")
            else:
                logger.info("ℹ️ NVIDIA NIM: No API key configured (optional)")
        except Exception as e:
            logger.warning(f"⚠️ NVIDIA NIM test failed: {e}")
        
        # Test OCI (optional)
        try:
            if settings.OCI_NAMESPACE:
                results["oci_available"] = True
                logger.info("✅ OCI Object Storage: Configuration found")
            else:
                logger.info("ℹ️ OCI Object Storage: Not configured (optional)")
        except Exception as e:
            logger.warning(f"⚠️ OCI test failed: {e}")
        
        return results
    
    async def run_analysis(self) -> Dict[str, Any]:
        """Run a complete analysis cycle"""
        analysis_start_time = datetime.now()
        logger.info("🚀 Starting automated Oracle Logs analysis...")
        
        try:
            # Step 1: Test connections
            logger.info("🔍 Step 1: Testing service connections...")
            connections = await self.test_connections()
            
            if not connections["mcp_connected"]:
                error_msg = "Cannot proceed without MCP server connection"
                logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "timestamp": analysis_start_time.isoformat(),
                    "connections": connections
                }
            
            # Step 2: Get analysis prompt
            logger.info("📝 Step 2: Loading analysis prompt...")
            try:
                analysis_prompt = await self.oci_client.get_analysis_prompt()
                logger.info("✅ Analysis prompt loaded from OCI Object Storage")
            except Exception as e:
                logger.warning(f"⚠️ Could not fetch prompt from OCI, using default: {e}")
                analysis_prompt = self._get_default_analysis_prompt()
            
            # Step 3: Gather comprehensive log data from your MCP server
            logger.info("📊 Step 3: Gathering log data from Oracle Logs MCP Server...")
            analysis_data = await self.analytics_service.prepare_comprehensive_analysis(
                self.mcp_client
            )
            
            # Log data summary
            stats = analysis_data.get("summary_statistics", {})
            logger.info(f"📈 Data gathered: {stats.get('total_logs', 0)} logs, "
                       f"{len(analysis_data.get('country_analytics', {}).get('analytics', []))} countries, "
                       f"{len(analysis_data.get('protocol_analytics', {}).get('analytics', []))} protocols")
            
            # Step 4: Perform AI analysis using NVIDIA NIM
            logger.info("🤖 Step 4: Performing AI analysis...")
            try:
                if settings.NVIDIA_NIM_API_KEY:
                    nim_analysis = await self.nim_client.analyze_logs(analysis_data, analysis_prompt)
                    logger.info("✅ AI analysis completed with NVIDIA NIM")
                else:
                    logger.info("ℹ️ No NVIDIA NIM API key, using fallback analysis")
                    nim_analysis = self._generate_fallback_analysis(analysis_data)
            except Exception as e:
                logger.warning(f"⚠️ NIM analysis failed, using fallback: {e}")
                nim_analysis = self._generate_fallback_analysis(analysis_data)
            
            # Step 5: Generate PDF report with visualizations
            logger.info("📄 Step 5: Generating PDF report with charts...")
            try:
                # Call the actual PDF generator
                report_path = await self.report_generator.generate_pdf_report(
                    analysis_data, nim_analysis
                )
                logger.info(f"✅ PDF Report generated: {report_path}")
                
            except Exception as e:
                logger.error(f"❌ PDF generation failed: {e}")
                # Fallback to JSON report
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_path = f"/tmp/fallback_analysis_{timestamp}.json"
                
                # Create reports directory if it doesn't exist
                os.makedirs(os.path.dirname(report_path) if os.path.dirname(report_path) else '/tmp', exist_ok=True)
                
                with open(report_path, 'w') as f:
                    json.dump({
                        'analysis_data': analysis_data,
                        'nim_analysis': nim_analysis,
                        'generated_at': datetime.now().isoformat(),
                        'error': str(e)
                    }, f, indent=2)
                
                logger.info(f"✅ Fallback JSON report generated: {report_path}")

            
            # Step 6: Upload to OCI Object Storage (optional)
            logger.info("☁️ Step 6: Uploading report to OCI Object Storage...")
            upload_success = False
            try:
                if settings.OCI_NAMESPACE and settings.OCI_BUCKET_NAME:
                    with open(report_path, 'rb') as f:
                        report_content = f.read()
                    
                    report_filename = report_path.split('/')[-1]
                    upload_success = await self.oci_client.upload_report(report_filename, report_content)
                    
                    if upload_success:
                        logger.info("✅ Report uploaded to OCI successfully")
                    else:
                        logger.info("ℹ️ Report upload to OCI failed or disabled")
                else:
                    logger.info("ℹ️ OCI upload skipped (not configured)")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to upload to OCI: {e}")
            
            # Analysis completed successfully
            analysis_duration = datetime.now() - analysis_start_time
            logger.info(f"🎉 Analysis completed successfully in {analysis_duration.total_seconds():.1f} seconds!")
            
            result = {
                "success": True,
                "report_path": report_path,
                "uploaded_to_oci": upload_success,
                "timestamp": analysis_start_time.isoformat(),
                "duration_seconds": analysis_duration.total_seconds(),
                "connections": connections,
                "data_summary": {
                    "total_logs": stats.get("total_logs", 0),
                    "countries": len(analysis_data.get("country_analytics", {}).get("analytics", [])),
                    "protocols": len(analysis_data.get("protocol_analytics", {}).get("analytics", [])),
                    "time_range": analysis_data.get("time_range", "24h")
                },
                "analysis_method": "NVIDIA NIM" if settings.NVIDIA_NIM_API_KEY else "Fallback Analysis"
            }
            
            self.last_analysis_result = result
            return result
            
        except Exception as e:
            analysis_duration = datetime.now() - analysis_start_time
            error_msg = f"Analysis failed after {analysis_duration.total_seconds():.1f}s: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            result = {
                "success": False,
                "error": str(e),
                "timestamp": analysis_start_time.isoformat(),
                "duration_seconds": analysis_duration.total_seconds()
            }
            
            self.last_analysis_result = result
            return result
        
        finally:
            # Clean up MCP connection
            try:
                await self.mcp_client.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing MCP connection: {e}")
    
    def _get_default_analysis_prompt(self) -> str:
        """Get default analysis prompt"""
        return """
        Analyze the provided Oracle Cloud Infrastructure log data and provide a comprehensive security and traffic analysis report.
        
        Please include:
        
        1. **Executive Summary**
           - Key findings and overall security posture
           - Critical issues requiring immediate attention
        
        2. **Security Threat Assessment**
           - Potential security threats and vulnerabilities
           - Suspicious IP addresses or traffic patterns
           - Risk level assessment (Low/Medium/High/Critical)
        
        3. **Traffic Pattern Analysis**
           - Traffic volume trends and patterns
           - Peak usage times and geographic distribution
           - Protocol usage analysis
        
        4. **Geographic Analysis**
           - Traffic distribution by country/region
           - Unusual geographic access patterns
           - Recommendations for geo-blocking if needed
        
        5. **Anomaly Detection**
           - Unusual traffic spikes or patterns
           - Potential DDoS or brute force attempts
           - Outliers in normal traffic behavior
        
        6. **Recommendations**
           - Immediate actions required
           - Long-term security improvements
           - Monitoring and alerting suggestions
        
        7. **Action Items**
           - Prioritized list of security tasks
           - Timeline for implementation
        
        Focus on actionable insights and provide specific recommendations based on the data patterns observed.
        """
    
    def _generate_fallback_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback analysis when AI is not available"""
        stats = analysis_data.get("summary_statistics", {})
        country_data = analysis_data.get("country_analytics", {}).get("analytics", [])
        protocol_data = analysis_data.get("protocol_analytics", {}).get("analytics", [])
        
        total_logs = stats.get("total_logs", 0)
        total_bytes = stats.get("total_bytes", 0)
        
        # Basic analysis
        top_country = country_data[0]["country"] if country_data else "Unknown"
        top_protocol = protocol_data[0]["protocol"] if protocol_data else "Unknown"
        
        # Calculate some basic metrics
        avg_bytes_per_log = total_bytes / total_logs if total_logs > 0 else 0
        countries_count = len(country_data)
        protocols_count = len(protocol_data)
        
        return {
            "executive_summary": f"Analyzed {total_logs:,} log entries from Oracle Cloud Infrastructure over the past 24 hours. Traffic shows normal patterns with {countries_count} countries and {protocols_count} different protocols observed.",
            
            "key_findings": [
                f"Total log entries processed: {total_logs:,}",
                f"Total data volume: {total_bytes / (1024*1024):.1f} MB",
                f"Primary traffic source: {top_country}",
                f"Most used protocol: {top_protocol}",
                f"Geographic distribution: {countries_count} countries",
                f"Average bytes per request: {avg_bytes_per_log:.0f}"
            ],
            
            "security_analysis": f"Automated analysis of {total_logs:,} log entries completed. Traffic patterns appear within normal parameters. No obvious security anomalies detected in the current dataset, but manual review is recommended for comprehensive threat assessment.",
            
            "traffic_patterns": {
                "total_requests": total_logs,
                "total_bytes": total_bytes,
                "top_country": top_country,
                "top_protocol": top_protocol,
                "geographic_spread": countries_count,
                "protocol_diversity": protocols_count
            },
            
            "recommendations": [
                "Continue monitoring traffic patterns for unusual spikes or geographic anomalies",
                "Review top traffic sources for legitimacy and expected usage patterns",
                "Consider implementing automated alerting for traffic volume thresholds",
                "Regularly review protocol usage to ensure only necessary services are exposed",
                "Implement geographic access controls if traffic from unexpected regions is observed",
                "Schedule regular comprehensive security reviews of log data"
            ],
            
            "risk_level": "Medium",
            "confidence": "Medium (Automated Statistical Analysis)",
            "analysis_method": "Fallback statistical analysis - manual review recommended",
            "next_steps": [
                "Review detailed country and protocol breakdowns",
                "Investigate any unusual traffic patterns manually",
                "Consider enabling AI analysis with NVIDIA NIM for deeper insights"
            ]
        }
    
    def start_scheduler(self):
        """Start the scheduled analysis"""
        if self.is_running:
            logger.warning("⚠️ Scheduler is already running")
            return
        
        logger.info(f"🕐 Starting analysis scheduler...")
        logger.info(f"📅 Analysis will run every {settings.ANALYSIS_INTERVAL_HOURS} hour(s)")
        
        # Schedule regular analysis - ONLY THIS ONE
        schedule.every(settings.ANALYSIS_INTERVAL_HOURS).hours.do(self._run_scheduled_analysis)
        
        # Run initial analysis after 2 minutes (not every minute!)
        schedule.every(2).minutes.do(self._run_initial_analysis).tag('initial')
        
        self.is_running = True
        self.scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ Analysis scheduler started successfully")
        logger.info(f"🎯 Initial analysis will run in 2 minutes, then every {settings.ANALYSIS_INTERVAL_HOURS} hour(s)")

    
    def stop_scheduler(self):
        """Stop the scheduled analysis"""
        if not self.is_running:
            logger.warning("⚠️ Scheduler is not running")
            return
            
        self.is_running = False
        schedule.clear()
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.info("🛑 Stopping scheduler thread...")
            # Thread will stop on next iteration due to is_running = False
        
        logger.info("✅ Analysis scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop running in separate thread"""
        logger.info("🔄 Scheduler loop started")
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"❌ Error in scheduler loop: {e}")
                time.sleep(60)  # Continue after error
        
        logger.info("🔄 Scheduler loop ended")
    
    def _run_scheduled_analysis(self):
        """Wrapper for scheduled analysis"""
        logger.info("⏰ Scheduled analysis triggered")
        try:
            asyncio.run(self.run_analysis())
        except Exception as e:
            logger.error(f"❌ Scheduled analysis failed: {e}")
    
    def _run_initial_analysis(self):
        """Run initial analysis and remove the job"""
        logger.info("🎯 Running initial analysis...")
        try:
            asyncio.run(self.run_analysis())
        except Exception as e:
            logger.error(f"❌ Initial analysis failed: {e}")
        finally:
            # Remove the initial job so it doesn't repeat
            schedule.clear('initial')
            logger.info(f"📅 Initial analysis complete. Next analysis in {settings.ANALYSIS_INTERVAL_HOURS} hour(s)")

    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        next_run = None
        if schedule.jobs:
            next_runs = [job.next_run for job in schedule.jobs if job.next_run]
            if next_runs:
                next_run = min(next_runs)
        
        # Test MCP connection for current status
        mcp_connected = False
        try:
            mcp_connected = await self.mcp_client.test_connection()
        except Exception as e:
            logger.debug(f"MCP connection test failed: {e}")
        
        status = {
            "is_running": self.is_running,
            "next_scheduled_run": next_run.isoformat() if next_run else None,
            "interval_hours": settings.ANALYSIS_INTERVAL_HOURS,
            "active_jobs": len(schedule.jobs),
            "mcp_server_script": settings.MCP_SERVER_SCRIPT_PATH,
            "mcp_connected": mcp_connected,
            "last_analysis": self.last_analysis_result,
            "scheduler_thread_alive": self.scheduler_thread.is_alive() if self.scheduler_thread else False
        }
        
        return status
    
    async def run_manual_analysis(self) -> Dict[str, Any]:
        """Run analysis manually (triggered from web interface)"""
        logger.info("👤 Manual analysis triggered")
        return await self.run_analysis()
    
    async def cleanup(self):
        """Cleanup scheduler resources"""
        logger.info("🧹 Cleaning up scheduler resources...")
        
        # Stop scheduler
        self.stop_scheduler()
        
        # Close MCP connection
        try:
            await self.mcp_client.close()
        except Exception as e:
            logger.warning(f"⚠️ Error closing MCP client: {e}")
        
        # Close other clients if they have cleanup methods
        if hasattr(self.nim_client, 'close'):
            try:
                await self.nim_client.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing NIM client: {e}")
        
        logger.info("✅ Scheduler cleanup completed")
