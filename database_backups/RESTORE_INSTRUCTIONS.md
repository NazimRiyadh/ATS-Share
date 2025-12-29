# Database Restore Instructions

## Files Included

- `postgres_ats_db.sql` (23.43 MB) - PostgreSQL database backup
- `neo4j_graph.dump` (0.27 MB) - Neo4j knowledge graph backup
- `ingestion_state.json` (0.02 MB) - Ingestion tracking file

**Total backup size**: 23.72 MB

All data is included - no re-ingestion needed!

## Team Setup with Database Restore

### Step 1: Extract and Setup

```bash
# Extract zip and navigate
cd ATS-Share

# Copy environment
copy .env.example .env

# Activate venv
.\venv\Scripts\activate
```

### Step 2: Start Databases

```bash
docker-compose up -d postgres neo4j redis

# Wait 30 seconds for services to be healthy
timeout /t 30
```

### Step 3: Restore PostgreSQL

```bash
# Import PostgreSQL backup
docker-compose exec -T postgres psql -U postgres ats_db < database_backups\postgres_ats_db.sql

# Verify import
docker-compose exec postgres psql -U postgres -d ats_db -c "SELECT COUNT(*) FROM resumes;"
```

### Step 4: Restore Neo4j

```bash
# Stop Neo4j
docker-compose stop neo4j

# Copy dump file into container
docker cp database_backups\neo4j_graph.dump ats-neo4j:/data/neo4j.dump

# Restore from dump
docker-compose run --rm neo4j neo4j-admin database load neo4j --from-path=/data

# Start Neo4j
docker-compose up -d neo4j

# Wait for Neo4j to be ready (30 seconds)
timeout /t 30
```

### Step 5: Copy Ingestion State

```bash
# Copy ingestion tracking file
copy database_backups\ingestion_state.json data\ingestion_state.json
```

### Step 6: Start API

```bash
uvicorn api.main:app --reload
```

### Step 7: Verify

```bash
# Open http://localhost:8000/health
# Should return: {"status": "healthy", ...}

# Check data
curl http://localhost:8000/analyze -X POST -H "Content-Type: application/json" -d "{\"job_id\":\"test\",\"query\":\"Find Python developers\",\"top_k\":5}"
```

## What's Restored

✅ **PostgreSQL**: All resume data, candidate info, metadata  
✅ **Neo4j**: Complete knowledge graph with all relationships
✅ **Ingestion State**: Tracking of processed files

**Your team gets instant access to all data - no waiting for re-ingestion!**

## If You Want to Re-ingest Instead

Run the rebuild script to regenerate Neo4j from PostgreSQL:

```bash
python scripts/rebuild_graph.py
```

This will recreate the knowledge graph from the PostgreSQL data.

## Alternative: Fresh Setup

If restore has issues, team can do fresh ingestion:

```bash
# Initialize fresh databases
python scripts/init_db.py

# Ingest resumes (if included in zip)
python scripts/ingest_resumes.py --dir ./data/resumes --batch-size 5
```

## Troubleshooting

### "psql: command not found"

The restore command runs inside the docker container, not on your machine.

### "relation does not exist"

Run `python scripts/init_db.py` first to create schema.

### "Neo4j graph is empty"

This is expected. Either run `python scripts/rebuild_graph.py` or let it build naturally during queries.
