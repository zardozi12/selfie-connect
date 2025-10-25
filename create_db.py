#!/usr/bin/env python3
"""
Create PhotoVault database and initialize schema
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import init_db, close_db

async def create_database():
    """Create and initialize the PhotoVault database"""
    print("Initializing PhotoVault database...")
    
    try:
        await init_db()
        print("Database initialized successfully!")
        
        # Test database connection
        from tortoise import Tortoise
        from app.models.user import User
        
        # Create a test user if none exists
        user_count = await User.all().count()
        if user_count == 0:
            print("Creating test user...")
            test_user = await User.create(
                email="test@example.com",
                name="Test User",
                hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeWtK4t8L8Q5LQv3c"  # "TestPassword123!"
            )
            print(f"Test user created: {test_user.email}")
        else:
            print(f"Found {user_count} existing users")
            
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False
    finally:
        await close_db()
    
    return True

if __name__ == "__main__":
    success = asyncio.run(create_database())
    if success:
        print("PhotoVault database setup complete!")
        sys.exit(0)
    else:
        print("Database setup failed!")
        sys.exit(1)