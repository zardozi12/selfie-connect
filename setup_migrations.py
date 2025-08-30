#!/usr/bin/env python3
"""
Aerich migration setup script for PhotoVault
"""
import asyncio
import sys
import os
import subprocess

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import TORTOISE_ORM
from tortoise import Tortoise


async def setup_migrations():
    """Set up and run Aerich migrations"""
    print("Setting up Aerich migrations...")
    
    try:
        # Initialize Tortoise ORM
        await Tortoise.init(config=TORTOISE_ORM)
        
        # Run Aerich init (creates migration tables)
        print("Running Aerich init...")
        result = subprocess.run([
            "aerich", "init", "-t", "app.db.TORTOISE_ORM"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Aerich init output: {result.stdout}")
            print(f"Aerich init error: {result.stderr}")
            # Continue anyway, might already be initialized
        
        # Run Aerich init-db (creates initial migration)
        print("Running Aerich init-db...")
        result = subprocess.run([
            "aerich", "init-db"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Aerich init-db output: {result.stdout}")
            print(f"Aerich init-db error: {result.stderr}")
        
        # Run Aerich migrate (applies migrations)
        print("Running Aerich migrate...")
        result = subprocess.run([
            "aerich", "migrate"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Aerich migrate output: {result.stdout}")
            print(f"Aerich migrate error: {result.stderr}")
        
        # Run Aerich upgrade (applies pending migrations)
        print("Running Aerich upgrade...")
        result = subprocess.run([
            "aerich", "upgrade"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migrations completed successfully")
        else:
            print(f"Aerich upgrade output: {result.stdout}")
            print(f"Aerich upgrade error: {result.stderr}")
        
        # Close connections
        await Tortoise.close_connections()
        
    except Exception as e:
        print(f"❌ Migration setup failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(setup_migrations())
    if not success:
        sys.exit(1)
