@echo off
echo ===================================================
echo   ATS System - Starting API Server
echo ===================================================

set VENV_DIR=venv
if exist "venv312" set VENV_DIR=venv312

if not exist "%VENV_DIR%" (
    echo [ERROR] '%VENV_DIR%' not found. Please run setup_env.bat first or check your venv folder.
    pause
    exit /b 1
)

:: Activate venv (optional for direct call, but good practice)
call .\%VENV_DIR%\Scripts\activate.bat

echo [INFO] Checking Docker containers...
docker-compose ps | findstr "Up" >nul
if %errorlevel% neq 0 (
    echo [WARN] Docker containers might not be running. Starting them...
    docker-compose up -d
)

echo [INFO] Starting Uvicorn Server...
cd api
uvicorn main:app --reload --port 8000
pause