@echo off
setlocal
echo ===================================================
echo   ATS System - Environment Setup Script
echo ===================================================

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)
echo [OK] Python found.

:: 2. Create/Check Virtual Environment
if exist "venv312" (
    echo [INFO] Found existing 'venv312'. Using it.
    set VENV_DIR=venv312
) else (
    if not exist "venv" (
        echo [INFO] Creating virtual environment 'venv'...
        python -m venv venv
        if %errorlevel% neq 0 (
            echo [ERROR] Failed to create venv.
            pause
            exit /b 1
        )
        echo [OK] venv created.
    ) else (
        echo [INFO] 'venv' already exists.
    )
    set VENV_DIR=venv
)

:: 3. Setup .env
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example...
        copy .env.example .env >nul
        echo [OK] .env created. Please edit it with your secrets if needed.
    ) else (
        echo [WARN] .env.example not found. Skipping .env creation.
    )
) else (
    echo [INFO] .env already exists.
)

:: 4. Install Dependencies
echo [INFO] Installing dependencies in %VENV_DIR%...
.\%VENV_DIR%\Scripts\python -m pip install --upgrade pip
.\%VENV_DIR%\Scripts\pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.

:: 5. Pull Ollama Model
echo [INFO] Pulling Ollama model (llama3.1:8b)...
ollama pull llama3.1:8b
if %errorlevel% neq 0 (
    echo [WARN] Failed to pull model via Ollama. Is Ollama running?
    echo        Please run 'ollama pull llama3.1:8b' manually later.
) else (
    echo [OK] Model pulled.
)

echo ===================================================
echo   Setup Complete!
echo ===================================================
echo.
echo Next steps:
echo 1. Start databases: docker-compose up -d
echo 2. Initialize DB:   .\venv\Scripts\python scripts/init_db.py
echo 3. Ingest data:     .\venv\Scripts\python scripts/ingest_resumes.py ...
echo 4. Run API:         run_api.bat
echo.
pause
