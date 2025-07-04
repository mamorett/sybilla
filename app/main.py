import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
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
import mimetypes

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
async def dashboard(request: Request, page: int = Query(1, ge=1)):
    """Main dashboard"""
    per_page = 24
    status = await scheduler.get_scheduler_status() if scheduler else {"is_running": False}
    
    # Get analysis runs
    all_analysis_runs = get_analysis_runs()

    # Paginate the runs
    total_runs = len(all_analysis_runs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_runs = all_analysis_runs[start:end]

    total_pages = (total_runs + per_page - 1) // per_page

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "scheduler_status": status,
        "analysis_runs": paginated_runs,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_runs": total_runs,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_num": page - 1 if page > 1 else None,
            "next_num": page + 1 if page < total_pages else None,
        }
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
async def list_runs(page: int = Query(1, ge=1)):
    """List all analysis runs"""
    per_page = 24
    all_runs = get_analysis_runs()
    total_runs = len(all_runs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_runs = all_runs[start:end]
    total_pages = (total_runs + per_page - 1) // per_page

    return {
        "runs": paginated_runs,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_runs": total_runs,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_num": page - 1 if page > 1 else None,
            "next_num": page + 1 if page < total_pages else None,
        }
    }

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

def process_markdown_images(content: str, run_id: str) -> str:
    """Process markdown content to fix image paths and add sizing"""
    # Pattern to match markdown images: ![alt](path)
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    
    def replace_image_path(match):
        alt_text = match.group(1)
        image_path = match.group(2)
        
        # If it's already a web URL, leave it as is
        if image_path.startswith(('http://', 'https://', '/')):
            return match.group(0)
        
        # Convert relative path to web-accessible path
        web_path = f"/reports/{run_id}/images/{os.path.basename(image_path)}"
        return f'![{alt_text}]({web_path})'
    
    return re.sub(image_pattern, replace_image_path, content)

@app.get("/report/{run_id}", response_class=HTMLResponse)
async def view_report(request: Request, run_id: str):
    """View analysis report in HTML format"""
    try:
        # Validate run_id format for security
        if not re.match(r'^[a-zA-Z0-9_-]+$', run_id):
            raise HTTPException(status_code=400, detail="Invalid run ID format")
        
        # Get report content
        report_path = Path("./reports") / run_id / "analysis_report.md"
        
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Process image paths in markdown
        processed_content = process_markdown_images(content, run_id)
        
        # Convert markdown to HTML
        html_content = markdown.markdown(processed_content, extensions=['tables', 'fenced_code', 'codehilite'])
        
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

@app.get("/reports/{run_id}/images/{filename}")
async def serve_report_image(run_id: str, filename: str):
    """Serve images from report directories"""
    # Validate run_id format for security
    if not re.match(r'^[a-zA-Z0-9_-]+$', run_id):
        raise HTTPException(status_code=400, detail="Invalid run ID format")
    
    # Validate filename for security (no path traversal)
    if not re.match(r'^[a-zA-Z0-9_.-]+$', filename) or '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Look for the image in the report directory
    report_dir = Path("./reports") / run_id
    
    # Common image locations in report directories
    possible_paths = [
        report_dir / filename,
        report_dir / "images" / filename,
        report_dir / "plots" / filename,
        report_dir / "charts" / filename,
    ]
    
    image_path = None
    for path in possible_paths:
        if path.exists() and path.is_file():
            image_path = path
            break
    
    if not image_path:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Determine media type
    media_type, _ = mimetypes.guess_type(str(image_path))
    if not media_type or not media_type.startswith('image/'):
        media_type = 'application/octet-stream'
    
    return FileResponse(
        image_path,
        media_type=media_type,
        filename=filename
    )

@app.get("/reports/{run_id}/files/{filename}")
async def serve_report_file(run_id: str, filename: str):
    """Serve any file from report directories"""
    # Validate run_id format for security
    if not re.match(r'^[a-zA-Z0-9_-]+$', run_id):
        raise HTTPException(status_code=400, detail="Invalid run ID format")
    
    # Validate filename for security (no path traversal)
    if not re.match(r'^[a-zA-Z0-9_.-]+$', filename) or '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Look for the file in the report directory
    report_dir = Path("./reports") / run_id
    file_path = report_dir / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    media_type, _ = mimetypes.guess_type(str(file_path))
    if not media_type:
        media_type = 'application/octet-stream'
    
    return FileResponse(
        file_path,
        media_type=media_type,
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
