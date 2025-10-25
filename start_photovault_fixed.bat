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
pip install --upgrade pip
pip install -r requirements.txt --upgrade

echo [3/8] Checking environment configuration...
if not exist ".env" (
    echo WARNING: .env file not found. Creating a basic one...
    echo DATABASE_URL=sqlite:///./dev.db > .env
    echo JWT_SECRET=your-super-secure-jwt-secret-key-at-least-32-characters >> .env
    echo CSRF_SECRET=your-super-secure-csrf-secret-key-at-least-32-characters >> .env
    echo MASTER_KEY=your-master-encryption-key-base64-encoded >> .env
    echo APP_ENV=development >> .env
    echo CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"] >> .env
    echo STORAGE_DRIVER=local >> .env
    echo STORAGE_DIR=./storage >> .env
)

echo [4/8] Creating storage directory...
if not exist "storage" mkdir storage

echo [5/8] Testing basic imports...
python -c "
try:
    from fastapi import FastAPI
    from fastapi_csrf_protect import CsrfProtect
    from slowapi import Limiter
    print('✓ All required modules imported successfully')
except ImportError as e:
    print(f'✗ Import error: {e}')
    exit(1)
"

echo [6/8] Starting PhotoVault Backend Server...
echo Server will start on http://127.0.0.1:8999
echo Swagger UI: http://127.0.0.1:8999/docs
echo ReDoc: http://127.0.0.1:8999/redoc
echo.

echo Starting server...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8999 --reload

pause