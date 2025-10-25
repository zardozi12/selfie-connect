#!/usr/bin/env python3
"""
PhotoVault Production Startup Script
Starts the production server with proper configuration for API documentation
"""

import uvicorn
import os
from app.config import settings

def start_production_server():
    """Start the production server with proper configuration"""
    print("🚀 Starting PhotoVault Production Server...")
    print(f"📊 API Documentation: http://localhost:8999/docs")
    print(f"📋 OpenAPI Schema: http://localhost:8999/openapi.json")
    print(f"🔍 ReDoc: http://localhost:8999/redoc")
    print("=" * 60)
    
    # Production server configuration
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # Bind to all interfaces
        port=8999,
        reload=False,    # Disable reload in production
        workers=2,       # Use multiple workers for production
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    start_production_server()