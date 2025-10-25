@echo off
echo ============================================================
echo    PhotoVault Error Checker
echo ============================================================
echo.

cd /d "d:\projects\photovault"

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Running comprehensive error check...
python check_all_errors.py

echo.
echo Press any key to exit...
pause > nul