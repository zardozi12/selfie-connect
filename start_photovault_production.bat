@echo off
echo ========================================
echo PhotoVault Production Startup Script
echo ========================================
echo.

echo [1/8] Checking Python environment...
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

echo [2/8] Installing/updating dependencies...
cd /d "d:\projects\photovault"
pip install -r requirements.txt --quiet

echo [3/8] Checking environment configuration...
if not exist ".env" (
    echo ERROR: .env file not found. Please create it with required variables.
    echo Required variables: DATABASE_URL, JWT_SECRET, CSRF_SECRET, MASTER_KEY
    pause
    exit /b 1
)

echo [4/8] Running database migrations...
python -m aerich upgrade

echo [5/8] Testing database connection...
python -c "
import asyncio
from app.db import init_db, close_db
async def test():
    try:
        await init_db()
        print('✓ Database connection successful')
        await close_db()
    except Exception as e:
        print(f'✗ Database connection failed: {e}')
        exit(1)
asyncio.run(test())
"

echo [6/8] Starting PhotoVault Backend Server...
echo Server will start on http://127.0.0.1:8999
echo Swagger UI: http://127.0.0.1:8999/docs
echo ReDoc: http://127.0.0.1:8999/redoc
echo.

start "PhotoVault Backend" cmd /k "echo PhotoVault Backend Server && cd /d d:\projects\photovault && python -m uvicorn app.main:app --host 127.0.0.1 --port 8999 --reload"

echo [7/8] Waiting for backend to start...
timeout /t 10 /nobreak >nul

echo [8/8] Testing API endpoints...
python test_all_endpoints.py

echo.
echo ========================================
echo PhotoVault is now running!
echo ========================================
echo Backend: http://127.0.0.1:8999
echo API Docs: http://127.0.0.1:8999/docs
echo Health Check: http://127.0.0.1:8999/health
echo ========================================
echo.
echo Press any key to exit this launcher...
pause > nul