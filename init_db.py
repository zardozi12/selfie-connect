#!/usr/bin/env python3
"""
Database initialization script for PhotoVault
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import init_db, TORTOISE_ORM
from tortoise import Tortoise


async def setup_database():
    """Initialize database and run migrations"""
    print("Setting up database...")
    
    try:
        # Initialize Tortoise ORM
        await Tortoise.init(config=TORTOISE_ORM)
        
        # Generate schemas
        await Tortoise.generate_schemas()
        print("✅ Database schemas generated successfully")
        
        # Close connections
        await Tortoise.close_connections()
        print("✅ Database setup completed")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        print("\nMake sure PostgreSQL is running and accessible.")
        print("You can start it with: docker compose up -d db")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(setup_database())
    if not success:
        sys.exit(1)
