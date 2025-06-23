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
import re
from datetime import datetime
from pathlib import Path
import markdown

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

def get_analysis_runs():
    """Get all analysis runs from reports directory"""
    reports_dir = Path("./reports")
    runs = []
    
    if not reports_dir.exists():
        return runs
    
    # Pattern to match directory names like sybylla-20250623_132354
    pattern = re.compile(r'^(.+)-(\d{8}_\d{6})$')
    
    for item in reports_dir.iterdir():
        if item.is_dir():
            match = pattern.match(item.name)
            if match:
                hostname, timestamp_str = match.groups()
                
                # Parse timestamp
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                except ValueError:
                    continue
                
                # Check for analysis report
                report_file = item / "analysis_report.md"
                status = "completed" if report_file.exists() else "failed"
                
                # Get file size if exists
                file_size = report_file.stat().st_size if report_file.exists() else 0
                
                runs.append({
                    "id": item.name,
                    "hostname": hostname,
                    "timestamp": timestamp,
                    "timestamp_str": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    "status": status,
                    "report_exists": report_file.exists(),
                    "file_size": file_size,
                    "directory": str(item)
                })
    
    # Sort by timestamp, newest first
    runs.sort(key=lambda x: x['timestamp'], reverse=True)
    return runs

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    status = await scheduler.get_scheduler_status() if scheduler else {"is_running": False}
    
    # Get analysis runs
    analysis_runs = get_analysis_runs()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "scheduler_status": status,
        "analysis_runs": analysis_runs
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

@app.get("/api/runs")
async def list_runs():
    """List all analysis runs"""
    runs = get_analysis_runs()
    return {"runs": runs}

@app.get("/api/runs/{run_id}/report")
async def get_report(run_id: str):
    """Get analysis report content"""
    # Validate run_id format for security
    if not re.match(r'^[a-zA-Z0-9_-]+$', run_id):
        raise HTTPException(status_code=400, detail="Invalid run ID format")
    
    report_path = Path("./reports") / run_id / "analysis_report.md"
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "run_id": run_id,
            "content": content,
            "html_content": markdown.markdown(content, extensions=['tables', 'fenced_code'])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading report: {str(e)}")

@app.get("/report/{run_id}", response_class=HTMLResponse)
async def view_report(request: Request, run_id: str):
    """View analysis report in HTML format"""
    try:
        # Get report content
        report_path = Path("./reports") / run_id / "analysis_report.md"
        
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Convert markdown to HTML
        html_content = markdown.markdown(content, extensions=['tables', 'fenced_code', 'codehilite'])
        
        # Get run info
        runs = get_analysis_runs()
        run_info = next((run for run in runs if run['id'] == run_id), None)
        
        return templates.TemplateResponse("report.html", {
            "request": request,
            "run_id": run_id,
            "run_info": run_info,
            "html_content": html_content,
            "markdown_content": content
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading report: {str(e)}")

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
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=9090,
        reload=True,
        log_level="info"
    )
