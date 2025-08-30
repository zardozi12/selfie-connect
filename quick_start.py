#!/usr/bin/env python3
"""
Quick Start Script for PhotoVault Backend
This script helps you get the PhotoVault backend running quickly.
"""

import os
import sys
import subprocess
import secrets
import string
from pathlib import Path


def generate_secret_key(length=32):
    """Generate a random secret key"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_env_file():
    """Create a .env file with default configuration"""
    env_content = f"""# PhotoVault Backend Configuration
# Generated automatically by quick_start.py

# Database Configuration
DATABASE_URL=postgresql://photovault:photovault123@localhost:5432/photovault

# Security Keys (Generated automatically - CHANGE THESE IN PRODUCTION!)
JWT_SECRET={generate_secret_key(64)}
MASTER_KEY={generate_secret_key(44)}  # Base64 encoded for Fernet

# Application Settings
APP_ENV=dev
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000

# Storage Configuration
STORAGE_DRIVER=local
STORAGE_DIR=./storage

# AI/ML Settings
EMBEDDINGS_PROVIDER=phash  # Options: phash, clip
CLIP_MODEL=clip-ViT-B-32

# Geocoding (Optional - requires email for Nominatim)
ENABLE_GEOCODER=true
GEOCODER_EMAIL=your-email@example.com

# Cloud Storage (Optional - for Cloudinary free tier)
# CLOUDINARY_CLOUD_NAME=your-cloud-name
# CLOUDINARY_API_KEY=your-api-key
# CLOUDINARY_API_SECRET=your-api-secret
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env file with default configuration")
    print("⚠️  IMPORTANT: Change JWT_SECRET and MASTER_KEY in production!")


def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    try:
        import fastapi
        import tortoise
        import cv2
        import numpy
        import PIL
        print("✅ All Python dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False


def check_postgres():
    """Check if PostgreSQL is running and accessible"""
    print("🔍 Checking PostgreSQL connection...")
    
    try:
        import asyncpg
        import asyncio
        
        async def test_connection():
            try:
                conn = await asyncpg.connect(
                    "postgresql://photovault:photovault123@localhost:5432/photovault"
                )
                await conn.close()
                return True
            except Exception:
                return False
        
        result = asyncio.run(test_connection())
        if result:
            print("✅ PostgreSQL connection successful")
            return True
        else:
            print("❌ Cannot connect to PostgreSQL")
            print("Make sure PostgreSQL is running and the database exists")
            return False
    except Exception as e:
        print(f"❌ PostgreSQL check failed: {e}")
        return False


def setup_database():
    """Set up the database with migrations"""
    print("🗄️  Setting up database...")
    
    try:
        # Run database initialization
        result = subprocess.run([sys.executable, "init_db.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Database setup completed")
            return True
        else:
            print(f"❌ Database setup failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Database setup error: {e}")
        return False


def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting PhotoVault backend server...")
    print("📖 API Documentation will be available at: http://127.0.0.1:8999/docs")
    print("🔗 OpenAPI Schema: http://127.0.0.1:8999/openapi.json")
    print("🏥 Health Check: http://127.0.0.1:8999/health")
    print("\nPress Ctrl+C to stop the server\n")
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "127.0.0.1", 
            "--port", "8999", 
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n👋 Server stopped")


def main():
    """Main quick start function"""
    print("🎉 Welcome to PhotoVault Backend Quick Start!")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("app").exists():
        print("❌ Please run this script from the PhotoVault project root directory")
        sys.exit(1)
    
    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        print("📝 Creating .env file...")
        create_env_file()
    else:
        print("✅ .env file already exists")
    
    # Check dependencies
    if not check_dependencies():
        print("\n💡 To install dependencies, run:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # Check PostgreSQL
    if not check_postgres():
        print("\n💡 To set up PostgreSQL with Docker, run:")
        print("   docker-compose up postgres -d")
        print("\n💡 Or install PostgreSQL locally and create the database:")
        print("   createdb photovault")
        print("   psql photovault -c 'CREATE EXTENSION vector;'")
        sys.exit(1)
    
    # Setup database
    if not setup_database():
        print("\n💡 Try running the database setup manually:")
        print("   python init_db.py")
        sys.exit(1)
    
    print("\n🎯 All checks passed! Starting server...")
    start_server()


if __name__ == "__main__":
    main()
