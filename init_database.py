#!/usr/bin/env python3
"""
Initialize PhotoVault database with proper schema
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.db import init_db, close_db
from app.models.user import User

async def initialize_database():
    """Initialize the PhotoVault database with proper schema"""
    print("🔧 Initializing PhotoVault database...")
    
    try:
        await init_db()
        print("✅ Database initialized successfully!")
        
        # Test database connection and create test user if needed
        from tortoise import Tortoise
        
        # Check if we can query users
        try:
            user_count = await User.all().count()
            print(f"📊 Found {user_count} existing users")
            
            if user_count == 0:
                print("👤 Creating test user...")
                test_user = await User.create(
                    email="test@example.com",
                    name="Test User",
                    password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeWtK4t8L8Q5LQv3c",  # "TestPassword123!"
                    dek_encrypted_b64="test_dek_encrypted",
                    is_admin=False
                )
                print(f"✅ Test user created: {test_user.email}")
        except Exception as e:
            print(f"⚠️  Could not create test user: {e}")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False
    finally:
        await close_db()
    
    return True

if __name__ == "__main__":
    success = asyncio.run(initialize_database())
    if success:
        print("🎉 PhotoVault database setup complete!")
        sys.exit(0)
    else:
        print("💥 Database setup failed!")
        sys.exit(1)