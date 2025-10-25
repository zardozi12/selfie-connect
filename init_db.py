#!/usr/bin/env python3
"""
Initialize PhotoVault database for Docker deployment
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import init_db, close_db

async def initialize_database():
    """Initialize the database for Docker deployment"""
    print("Initializing PhotoVault database...")
    
    try:
        await init_db()
        print("Database initialized successfully!")
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False
    finally:
        await close_db()

if __name__ == "__main__":
    success = asyncio.run(initialize_database())
    if not success:
        sys.exit(1)
