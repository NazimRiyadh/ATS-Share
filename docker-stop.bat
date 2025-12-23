@echo off
REM Docker Stop Script
REM Stops all ATS containers while preserving data

echo Stopping all ATS containers...
docker-compose stop

echo.
echo All containers stopped. Data is preserved in Docker volumes.
echo.
echo To start again:    docker-compose up -d
echo To remove containers (keeps data):  docker-compose down
echo To remove everything including data: docker-compose down -v
echo.
pause
