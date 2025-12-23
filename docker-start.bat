@echo off
REM Quick Start Script for Docker Deployment
REM Starts all ATS services in Docker containers

echo ========================================
echo   LightRAG ATS - Docker Quick Start
echo ========================================
echo.

echo [1/5] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo Docker is installed.

echo.
echo [2/5] Checking Ollama...
ollama list >nul 2>&1
if errorlevel 1 (
    echo WARNING: Ollama is not running or not installed
    echo The application requires Ollama with llama3.1:8b and qwen2.5:3b models
    echo Install from: https://ollama.com/
    pause
)
echo Ollama is running.

echo.
echo [3/5] Building and starting containers...
docker-compose up -d
if errorlevel 1 (
    echo ERROR: Failed to start containers
    pause
    exit /b 1
)

echo.
echo [4/5] Waiting for services to be healthy (this may take 60-90 seconds)...
timeout /t 10 /nobreak >nul
docker-compose ps

echo.
echo [5/5] Initialization commands:
echo.
echo To initialize the database, run:
echo   docker-compose exec app python scripts/init_db.py
echo.
echo To ingest resumes, run:
echo   docker-compose exec app python scripts/ingest_resumes.py --dir /app/data/resumes --batch-size 5
echo.
echo ========================================
echo   Services are starting!
echo ========================================
echo.
echo API:          http://localhost:8000
echo API Docs:     http://localhost:8000/docs
echo Neo4j Browser: http://localhost:7474
echo.
echo View logs:    docker-compose logs -f app
echo Stop all:     docker-compose stop
echo.
pause
