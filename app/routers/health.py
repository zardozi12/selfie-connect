from fastapi import APIRouter
from tortoise import Tortoise
import time
import psutil
import os

router = APIRouter(prefix="/ops", tags=["ops"])

# Store startup time for uptime calculation
startup_time = time.time()

@router.get("/db-health")
async def db_health():
    """Simple database health check using Tortoise ORM"""
    try:
        # Test database connection
        await Tortoise.get_connection("default").execute_query("SELECT 1")
        return {"db_ok": True}
    except Exception as e:
        return {"db_ok": False, "error": str(e)}

@router.get("/metrics")
async def get_metrics():
    """Basic metrics endpoint for monitoring"""
    try:
        uptime_seconds = time.time() - startup_time
        try:
            memory_info = psutil.virtual_memory()
            memory_percent = memory_info.percent
            memory_available = round(memory_info.available / 1024 / 1024, 2)
        except:
            memory_percent = 0
            memory_available = 0
        
        return {
            "status": "healthy",
            "uptime_seconds": round(uptime_seconds, 2),
            "memory_usage_percent": memory_percent,
            "memory_available_mb": memory_available,
            "process_id": os.getpid(),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

from fastapi import Request

@router.get("/routes")
async def list_routes(request: Request):
    app = request.app
    routes = []
    for r in app.routes:
        path = getattr(r, "path", "")
        methods = list(getattr(r, "methods", []) or [])
        name = getattr(r, "name", "")
        routes.append({"path": path, "methods": methods, "name": name})
    return {"count": len(routes), "routes": routes}


