@echo off
setlocal enabledelayedexpansion

:: run_tests.bat
:: Automation script for the Local Testing Suite (Windows)

set PROJECT_ROOT=%~dp0
cd /d "%PROJECT_ROOT%"

echo ====================================================
echo   Setting up Local Testing Suite...
echo ====================================================

:: 1. Create virtual environment
if not exist ".venv" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/3] Virtual environment already exists.
)

:: 2. Activate and install dependencies
echo [2/3] Installing dependencies from requirements.txt...
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 3. Run the test script
echo [3/3] Running test_local.py...
set PYTHONPATH=%PROJECT_ROOT%
python test_local.py

:: Deactivate
call .venv\Scripts\deactivate

echo ====================================================
echo   Test run complete.
echo ====================================================
pause
