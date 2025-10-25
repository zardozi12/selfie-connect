# PhotoVault Production Startup Script for PowerShell
Write-Host "========================================" -ForegroundColor Green
Write-Host "PhotoVault Production Startup Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "[1/8] Checking Python environment..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.11+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[2/8] Installing/updating dependencies..." -ForegroundColor Yellow
Set-Location "d:\projects\photovault"
pip install -r requirements.txt --quiet --upgrade

Write-Host "[3/8] Checking environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found. Please create it with required variables." -ForegroundColor Red
    Write-Host "Required variables: DATABASE_URL, JWT_SECRET, CSRF_SECRET, MASTER_KEY" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[4/8] Running database migrations..." -ForegroundColor Yellow
python -m aerich upgrade

Write-Host "[5/8] Testing database connection..." -ForegroundColor Yellow
python -c @"
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
"@

Write-Host "[6/8] Starting PhotoVault Backend Server..." -ForegroundColor Yellow
Write-Host "Server will start on http://127.0.0.1:8999" -ForegroundColor Cyan
Write-Host "Swagger UI: http://127.0.0.1:8999/docs" -ForegroundColor Cyan
Write-Host "ReDoc: http://127.0.0.1:8999/redoc" -ForegroundColor Cyan
Write-Host ""

# Start the server in a new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'd:\projects\photovault'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8999 --reload"

Write-Host "[7/8] Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "[8/8] Testing API endpoints..." -ForegroundColor Yellow
python test_all_endpoints.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "PhotoVault is now running!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Backend: http://127.0.0.1:8999" -ForegroundColor Cyan
Write-Host "API Docs: http://127.0.0.1:8999/docs" -ForegroundColor Cyan
Write-Host "Health Check: http://127.0.0.1:8999/health" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to exit this launcher..." -ForegroundColor Yellow
Read-Host