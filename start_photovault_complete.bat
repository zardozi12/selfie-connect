@echo off
echo ========================================
echo    PhotoVault - Complete Fixed Startup
echo ========================================
echo.

echo [1/8] Stopping any existing processes...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul
timeout /t 2 /nobreak >nul

echo [2/8] Installing missing dependencies...
cd /d D:\projects\photovault
pip install fastapi-csrf-protect slowapi prometheus-client psutil >nul 2>&1

echo [3/8] Setting up environment variables...
set DATABASE_URL=sqlite://./photovault.db
set JWT_SECRET=dev-jwt-secret-key-change-in-production-must-be-32-chars-minimum
set MASTER_KEY=dev-master-encryption-key-change-in-production-32-chars-min
set CSRF_SECRET=dev-csrf-secret-key-change-in-production-32-chars-minimum
set METRICS_ENABLED=0
set APP_ENV=development

echo [4/8] Starting Backend Server (FastAPI)...
start "PhotoVault Backend" cmd /k "echo PhotoVault Backend Starting... && cd /d D:\projects\photovault && set DATABASE_URL=sqlite://./photovault.db && set JWT_SECRET=dev-jwt-secret-key-change-in-production-must-be-32-chars-minimum && set MASTER_KEY=dev-master-encryption-key-change-in-production-32-chars-min && set CSRF_SECRET=dev-csrf-secret-key-change-in-production-32-chars-minimum && set METRICS_ENABLED=0 && set APP_ENV=development && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [5/8] Waiting for backend to initialize...
timeout /t 10 /nobreak >nul

echo [6/8] Installing frontend dependencies...
cd /d D:\projects\photovaultfrontend
npm install >nul 2>&1

echo [7/8] Starting Frontend Server (Next.js)...
start "PhotoVault Frontend" cmd /k "echo PhotoVault Frontend Starting... && cd /d D:\projects\photovaultfrontend && npm run dev"

echo [8/8] Waiting for frontend to initialize...
timeout /t 15 /nobreak >nul

echo.
echo ========================================
echo    PhotoVault is now running!
echo ========================================
echo.
echo 🌐 Frontend: http://localhost:3000
echo 🔧 Backend API: http://localhost:8000
echo 📚 API Docs: http://localhost:8000/docs
echo 📊 Health Check: http://localhost:8000/health
echo.
echo Both servers are running in separate windows.
echo.
echo Press any key to exit this launcher...
pause > nul