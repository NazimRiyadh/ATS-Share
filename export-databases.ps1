# Export Database Backups for Distribution
# Run this script to create database dumps to include in your zip

Write-Host "=== Database Backup Export ===" -ForegroundColor Cyan
Write-Host ""

# Create backups directory
$BackupDir = ".\database_backups"
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
    Write-Host "Created backup directory: $BackupDir" -ForegroundColor Green
}

# 1. Export PostgreSQL
Write-Host "Exporting PostgreSQL database..." -ForegroundColor Yellow
try {
    docker-compose exec -T postgres pg_dump -U postgres ats_db > "$BackupDir\postgres_ats_db.sql"
    $pgSize = (Get-Item "$BackupDir\postgres_ats_db.sql").Length / 1MB
    Write-Host "[OK] PostgreSQL exported: $([math]::Round($pgSize, 2)) MB" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] PostgreSQL export failed: $_" -ForegroundColor Red
}

# 2. Export Neo4j
Write-Host "Exporting Neo4j graph database..." -ForegroundColor Yellow
try {
    # Create dump inside container
    docker-compose exec neo4j neo4j-admin database dump neo4j --to-path=/data 2>&1 | Out-Null
    
    # Copy dump to host
    docker cp ats-neo4j:/data/neo4j.dump "$BackupDir\neo4j_graph.dump"
    
    $neoSize = (Get-Item "$BackupDir\neo4j_graph.dump").Length / 1MB
    Write-Host "[OK] Neo4j exported: $([math]::Round($neoSize, 2)) MB" -ForegroundColor Green
} catch {
    Write-Host "[FAIL] Neo4j export failed: $_" -ForegroundColor Red
}

# 3. Copy ingestion state
Write-Host "Copying ingestion state..." -ForegroundColor Yellow
if (Test-Path ".\data\ingestion_state.json") {
    Copy-Item ".\data\ingestion_state.json" "$BackupDir\ingestion_state.json"
    Write-Host "[OK] Ingestion state copied" -ForegroundColor Green
} else {
    Write-Host "[WARN] No ingestion state found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
$totalSize = (Get-ChildItem $BackupDir -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "Total backup size: $([math]::Round($totalSize, 2)) MB" -ForegroundColor Cyan
Write-Host "Location: $BackupDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Include this folder in your distribution zip" -ForegroundColor Green
