# app/api/routes.py
from fastapi import APIRouter
import logging
import threading
import time
from datetime import datetime
from app.services.mcp_client import MCPClient

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple status
status = {
    "running": False,
    "message": "Ready",
    "progress": 0,
    "error": None,
    "results": None
}

@router.get("/status")
async def get_status():
    return status

@router.post("/test-mcp")
async def test_mcp():
    global status
    
    def run_test():
        global status
        status.update({"running": True, "message": "Testing...", "progress": 50, "error": None})
        
        try:
            client = MCPClient()
            success = client.test_connection()
            
            if success:
                status.update({
                    "running": False,
                    "message": "✅ MCP Test Successful!",
                    "progress": 100,
                    "error": None
                })
            else:
                status.update({
                    "running": False,
                    "message": "❌ MCP Test Failed",
                    "progress": 0,
                    "error": "Connection test failed"
                })
        except Exception as e:
            status.update({
                "running": False,
                "message": "❌ Test Error",
                "progress": 0,
                "error": str(e)
            })
    
    if not status["running"]:
        thread = threading.Thread(target=run_test)
        thread.start()
        return {"message": "Test started"}
    else:
        return {"error": "Already running"}

@router.post("/get-analytics")
async def get_analytics():
    global status
    
    def run_analytics():
        global status
        status.update({"running": True, "message": "Getting analytics...", "progress": 30, "error": None})
        
        try:
            client = MCPClient()
            result = client.get_traffic_analytics(time_range="1h", limit=10)
            
            if "error" in result:
                status.update({
                    "running": False,
                    "message": "❌ Analytics Failed",
                    "progress": 0,
                    "error": result["error"]
                })
            else:
                status.update({
                    "running": False,
                    "message": "✅ Analytics Complete!",
                    "progress": 100,
                    "error": None,
                    "results": result
                })
        except Exception as e:
            status.update({
                "running": False,
                "message": "❌ Analytics Error",
                "progress": 0,
                "error": str(e)
            })
    
    if not status["running"]:
        thread = threading.Thread(target=run_analytics)
        thread.start()
        return {"message": "Analytics started"}
    else:
        return {"error": "Already running"}
