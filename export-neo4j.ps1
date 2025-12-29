# Export Neo4j Database (requires stopping the database)
Write-Host "=== Neo4j Database Export ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "WARNING: This will temporarily stop Neo4j (30 seconds)" -ForegroundColor Yellow
Write-Host ""

$BackupDir = ".\database_backups"

# Stop Neo4j
Write-Host "Stopping Neo4j..." -ForegroundColor Yellow
docker-compose stop neo4j

# Wait for clean shutdown
Start-Sleep -Seconds 5

# Create dump
Write-Host "Creating Neo4j dump..." -ForegroundColor Yellow
docker-compose run --rm neo4j neo4j-admin database dump neo4j --to-path=/data

# Copy dump to backup folder
Write-Host "Copying dump file..." -ForegroundColor Yellow
docker cp ats-neo4j:/data/neo4j.dump "$BackupDir\neo4j_graph.dump"

# Restart Neo4j
Write-Host "Restarting Neo4j..." -ForegroundColor Yellow
docker-compose up -d neo4j

# Wait for startup
Write-Host "Waiting for Neo4j to be ready (20 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

# Show results
if (Test-Path "$BackupDir\neo4j_graph.dump") {
    $neoSize = (Get-Item "$BackupDir\neo4j_graph.dump").Length / 1MB
    Write-Host ""
    Write-Host "[OK] Neo4j exported: $([math]::Round($neoSize, 2)) MB" -ForegroundColor Green
    Write-Host "Location: $BackupDir\neo4j_graph.dump" -ForegroundColor Cyan
} else {
    Write-Host "[FAIL] Neo4j dump file not created" -ForegroundColor Red
}

Write-Host ""
Write-Host "Neo4j is now running again" -ForegroundColor Green
