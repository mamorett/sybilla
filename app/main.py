import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import uvicorn
import os

from app.scheduler import AnalysisScheduler
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: AnalysisScheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global scheduler
    
    # Startup
    logger.info("🚀 Starting Oracle Logs Analysis Frontend...")
    scheduler = AnalysisScheduler()
    scheduler.start_scheduler()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    if scheduler:
        await scheduler.cleanup()

# Create FastAPI app
app = FastAPI(
    title="Oracle Logs Analysis Frontend",
    description="Automated log analysis with NVIDIA NIM and OCI integration",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    status = await scheduler.get_scheduler_status() if scheduler else {"is_running": False}
    
    # Get recent reports
    reports_dir = settings.REPORT_OUTPUT_DIR
    recent_reports = []
    
    if os.path.exists(reports_dir):
        report_files = [f for f in os.listdir(reports_dir) if f.endswith('.pdf')]
        report_files.sort(key=lambda x: os.path.getctime(os.path.join(reports_dir, x)), reverse=True)
        recent_reports = report_files[:10]  # Last 10 reports
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "scheduler_status": status,
        "recent_reports": recent_reports
    })

@app.post("/api/run-analysis")
async def trigger_analysis(background_tasks: BackgroundTasks):
    """Manually trigger analysis"""
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    background_tasks.add_task(scheduler.run_analysis)
    return {"message": "Analysis started", "status": "running"}

@app.get("/api/status")
async def get_status():
    """Get current system status"""
    if not scheduler:
        return {"error": "Scheduler not initialized"}
    
    return await scheduler.get_scheduler_status()

@app.get("/api/reports")
async def list_reports():
    """List available reports"""
    reports_dir = settings.REPORT_OUTPUT_DIR
    reports = []
    
    if os.path.exists(reports_dir):
        for filename in os.listdir(reports_dir):
            if filename.endswith('.pdf'):
                filepath = os.path.join(reports_dir, filename)
                stat = os.stat(filepath)
                reports.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "download_url": f"/api/reports/{filename}"
                })
    
    reports.sort(key=lambda x: x['created'], reverse=True)
    return {"reports": reports}

@app.get("/api/reports/{filename}")
async def download_report(filename: str):
    """Download a specific report"""
    if not filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    filepath = os.path.join(settings.REPORT_OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        filepath,
        media_type='application/pdf',
        filename=filename
    )

@app.post("/api/scheduler/start")
async def start_scheduler():
    """Start the scheduler"""
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    scheduler.start_scheduler()
    return {"message": "Scheduler started"}

@app.post("/api/scheduler/stop")
async def stop_scheduler():
    """Stop the scheduler"""
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    scheduler.stop_scheduler()
    return {"message": "Scheduler stopped"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "scheduler_running": scheduler.is_running if scheduler else False,
        "timestamp": "2024-01-01T00:00:00Z"  # You'd use actual timestamp
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9090,
        reload=True,
        log_level="info"
    )
