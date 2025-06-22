import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import schedule
import time
from threading import Thread

from app.services.mcp_client import MCPClient
from app.services.nvidia_nim_client import NVIDIANIMClient
from app.services.oci_storage_client import OCIStorageClient
from app.services.analytics_service import AnalyticsService
from app.services.report_generator import ReportGenerator
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalysisScheduler:
    def __init__(self):
        self.mcp_client = MCPClient()
        self.nim_client = NVIDIANIMClient()
        self.oci_client = OCIStorageClient()
        self.analytics_service = AnalyticsService()
        self.report_generator = ReportGenerator()
        self.is_running = False
        self.scheduler_thread: Optional[Thread] = None
    
    async def run_analysis(self):
        """Run a complete analysis cycle"""
        try:
            logger.info("🚀 Starting automated log analysis...")
            
            # Step 1: Get analysis prompt from OCI
            logger.info("📝 Fetching analysis prompt from OCI Object Storage...")
            analysis_prompt = await self.oci_client.get_analysis_prompt()
            
            # Step 2: Gather comprehensive log data
            logger.info("📊 Gathering log data from MCP server...")
            analysis_data = await self.analytics_service.prepare_comprehensive_analysis(
                self.mcp_client
            )
            
            # Step 3: Perform AI analysis using NVIDIA NIM
            logger.info("🤖 Performing AI analysis with NVIDIA NIM...")
            nim_analysis = await self.nim_client.analyze_logs(analysis_data, analysis_prompt)
            
            # Step 4: Generate PDF report with charts
            logger.info("📄 Generating PDF report with visualizations...")
            report_path = await self.report_generator.generate_pdf_report(
                analysis_data, nim_analysis
            )
            
            # Step 5: Upload report to OCI (optional)
            logger.info("☁️ Uploading report to OCI Object Storage...")
            with open(report_path, 'rb') as f:
                report_content = f.read()
            
            report_filename = report_path.split('/')[-1]
            upload_success = await self.oci_client.upload_report(report_filename, report_content)
            
            if upload_success:
                logger.info(f"✅ Analysis complete! Report saved: {report_path} and uploaded to OCI")
            else:
                logger.info(f"✅ Analysis complete! Report saved locally: {report_path}")
                logger.warning("⚠️ Failed to upload report to OCI")
            
            return {
                "success": True,
                "report_path": report_path,
                "uploaded_to_oci": upload_success,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error during analysis: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def start_scheduler(self):
        """Start the scheduled analysis"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info(f"🕐 Starting scheduler - analysis will run every {settings.ANALYSIS_INTERVAL_HOURS} hour(s)")
        
        # Schedule the job
        schedule.every(settings.ANALYSIS_INTERVAL_HOURS).hours.do(self._run_scheduled_analysis)
        
        # Also run immediately on startup
        schedule.every().minute.do(self._run_initial_analysis).tag('initial')
        
        self.is_running = True
        self.scheduler_thread = Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ Scheduler started successfully")
    
    def stop_scheduler(self):
        """Stop the scheduled analysis"""
        self.is_running = False
        schedule.clear()
        logger.info("🛑 Scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _run_scheduled_analysis(self):
        """Wrapper for scheduled analysis"""
        logger.info("⏰ Scheduled analysis triggered")
        asyncio.run(self.run_analysis())
    
    def _run_initial_analysis(self):
        """Run initial analysis and remove the job"""
        logger.info("🎯 Running initial analysis...")
        asyncio.run(self.run_analysis())
        schedule.clear('initial')  # Remove the initial job
    
    async def get_scheduler_status(self) -> dict:
        """Get current scheduler status"""
        next_run = None
        if schedule.jobs:
            next_run = min([job.next_run for job in schedule.jobs if job.next_run])
        
        return {
            "is_running": self.is_running,
            "next_scheduled_run": next_run.isoformat() if next_run else None,
            "interval_hours": settings.ANALYSIS_INTERVAL_HOURS,
            "active_jobs": len(schedule.jobs)
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up scheduler resources...")
        self.stop_scheduler()
        await self.mcp_client.close()
        await self.nim_client.close()
