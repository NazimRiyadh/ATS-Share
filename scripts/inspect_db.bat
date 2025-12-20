@echo off
echo ===================================================
echo   ATS System - Inspecting Database
echo ===================================================

set VENV_DIR=venv
if exist "..\venv312" set VENV_DIR=venv312

if not exist "..\%VENV_DIR%" (
    echo [ERROR] '%VENV_DIR%' not found in parent directory.
    pause
    exit /b 1
)

:: Run the inspection script
..\%VENV_DIR%\Scripts\python inspect_db.py
pause
