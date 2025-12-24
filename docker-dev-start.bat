@echo off
REM Start databases only for local development
REM Run the application locally with venv

echo ========================================
echo   ATS - Development Mode (Databases Only)
echo ========================================
echo.

echo [1/2] Starting database containers...
docker-compose -f docker-compose.dev.yml up -d

if errorlevel 1 (
    echo ERROR: Failed to start containers
    echo Make sure Docker Desktop is running
    pause
    exit /b 1
)

echo.
echo [2/2] Waiting for services to be healthy...
timeout /t 15 /nobreak >nul

echo.
echo ========================================
echo   Databases Ready!
echo ========================================
echo.
echo PostgreSQL: localhost:5432
echo Neo4j Browser: http://localhost:7474
echo Redis: localhost:6379
echo.
echo Now run your application locally:
echo   1. Activate venv: .\venv\Scripts\activate
echo   2. Run API: python api/main.py
echo      OR: .\run_api.bat
echo.
echo Stop databases: docker-compose -f docker-compose.dev.yml stop
echo.
pause
