# PhotoVault Troubleshooting Guide

## 🚨 Common Issues & Solutions

### Issue 1: PowerShell Script Execution Error
**Error:** `start_photovault_production.bat : The term 'start_photovault_production.bat' is not recognized`

**Solutions:**
```powershell
# Option 1: Use .\ prefix
.\start_photovault_production.bat

# Option 2: Use the PowerShell script
.\start_photovault_production.ps1

# Option 3: Use the fixed batch file
.\start_photovault_fixed.bat
```

### Issue 2: Module Not Found Errors
**Error:** `ModuleNotFoundError: No module named 'fastapi_csrf_protect'`

**Solutions:**
```bash
# Install missing dependencies
pip install --upgrade pip
pip install -r requirements.txt --upgrade --force-reinstall

# If still failing, install individually
pip install fastapi-csrf-protect==0.3.2
pip install slowapi==0.1.9
pip install starlette==0.27.0
```

### Issue 3: Database Connection Issues
**Error:** Database connection failed

**Solutions:**
```bash
# For SQLite (development)
# No setup needed, will create automatically

# For PostgreSQL (production)
createdb photovault
psql -d photovault -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Issue 4: Port Already in Use
**Error:** `[Errno 10048] Only one usage of each socket address`

**Solutions:**
```bash
# Find process using port 8999
netstat -ano | findstr :8999

# Kill the process (replace PID with actual process ID)
taskkill /PID <process_id> /F

# Or use a different port
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Issue 5: Import Errors in Services
**Error:** `ImportError: cannot import name 'encryption' from 'app.services'`

**Solution:** Services are properly configured, but if issues persist:
```python
# Check if services/__init__.py exists and has proper exports
# File should contain all service imports
```

## 🔧 Quick Fixes

### Fix 1: Reinstall All Dependencies
```bash
cd d:\projects\photovault
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

### Fix 2: Reset Virtual Environment
```bash
# Deactivate current environment
deactivate

# Remove old environment
rmdir /s .venv

# Create new environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Fix 3: Use Alternative Startup Methods
```bash
# Method 1: Direct Python
cd d:\projects\photovault
python -m uvicorn app.main:app --host 127.0.0.1 --port 8999

# Method 2: Using start script
python start_photovault.py

# Method 3: Development mode
python -m uvicorn app.main:app --reload
```

## 🧪 Testing Commands

### Test 1: Check Dependencies
```bash
python -c "
import fastapi
import fastapi_csrf_protect
import slowapi
import tortoise
print('✓ All core dependencies available')
"
```

### Test 2: Test Database
```bash
python -c "
import asyncio
from app.db import init_db
asyncio.run(init_db())
print('✓ Database connection works')
"
```

### Test 3: Test API Endpoints
```bash
python test_all_endpoints.py
```

## 📋 Environment Setup Checklist

- [ ] Python 3.11+ installed
- [ ] Virtual environment activated
- [ ] All dependencies installed
- [ ] .env file created
- [ ] Database accessible
- [ ] Storage directory exists
- [ ] No port conflicts

## 🆘 Emergency Startup

If all else fails, use this minimal startup:

```bash
cd d:\projects\photovault
pip install fastapi uvicorn python-multipart
python -c "
from fastapi import FastAPI
app = FastAPI()

@app.get('/')
def read_root():
    return {'message': 'PhotoVault Emergency Mode'}

@app.get('/health')
def health():
    return {'status': 'ok'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8999)
"
```