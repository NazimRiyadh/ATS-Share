# Docker Deployment Guide

Complete guide for running LightRAG ATS in Docker containers.

## Quick Start

### 1. Prerequisites

- Docker Desktop installed and running
- Ollama installed on host machine with models pulled
- At least 8GB RAM allocated to Docker

### 2. Verify Ollama Setup

```powershell
# Check Ollama is running
ollama list

# Ensure required models are available
ollama pull llama3.1:8b
ollama pull qwen2.5:3b
```

### 3. Start All Services

```powershell
# Build and start all containers
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Initialize Database

```powershell
# Wait for services to be healthy (check with: docker-compose ps)
# Then initialize database schema
docker-compose exec app python scripts/init_db.py
```

### 5. Ingest Resumes

```powershell
# Place resume files in data/resumes/ directory
# Then run ingestion
docker-compose exec app python scripts/ingest_resumes.py --dir /app/data/resumes --batch-size 5
```

### 6. Access the API

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474 (user: `neo4j`, password: `ats_neo4j_password`)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Host Machine                        │
│                                                         │
│  ┌──────────────┐                                      │
│  │   Ollama     │  (Port 11434)                        │
│  │ llama3.1:8b  │                                      │
│  │ qwen2.5:3b   │                                      │
│  └──────────────┘                                      │
│         ▲                                               │
│         │ http://host.docker.internal:11434            │
│         │                                               │
│  ┌──────┴───────────────────────────────────────────┐  │
│  │          Docker Network (ats-network)            │  │
│  │                                                  │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │  │
│  │  │PostgreSQL│  │  Neo4j   │  │  Redis   │      │  │
│  │  │  +       │  │          │  │          │      │  │
│  │  │ pgvector │  │          │  │          │      │  │
│  │  └────▲─────┘  └────▲─────┘  └────▲─────┘      │  │
│  │       │             │             │             │  │
│  │       └─────────────┴─────────────┘             │  │
│  │                     │                           │  │
│  │              ┌──────▼──────┐                    │  │
│  │              │  FastAPI    │                    │  │
│  │              │     App     │  (Port 8000)       │  │
│  │              └─────────────┘                    │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Service Details

### FastAPI Application (`app`)

- **Image**: Built from local `Dockerfile`
- **Port**: 8000
- **Environment**: Loaded from `.env.docker`
- **Volumes**:
  - `./api`, `./src`, `./scripts`: Code (bind mounts for development)
  - `./rag_storage`: LightRAG storage
  - `./data`: Resume files and ingestion state
  - `model_cache`: Embedding models cache

### PostgreSQL (`postgres`)

- **Image**: `pgvector/pgvector:pg16`
- **Port**: 5432
- **Credentials**: `postgres` / `admin`
- **Database**: `ats_db`
- **Extensions**: pgvector (auto-enabled via init script)
- **Volume**: `ats_postgres_data`

### Neo4j (`neo4j`)

- **Image**: `neo4j:5.15-community`
- **Ports**: 7474 (browser), 7687 (bolt)
- **Credentials**: `neo4j` / `ats_neo4j_password`
- **Plugins**: APOC
- **Volumes**: `ats_neo4j_data`, `ats_neo4j_logs`

### Redis (`redis`)

- **Image**: `redis:alpine`
- **Port**: 6379
- **Volume**: `ats_redis_data`

## Common Operations

### Container Management

```powershell
# Start services
docker-compose up -d

# Stop services (keeps data)
docker-compose stop

# Stop and remove containers (keeps data in volumes)
docker-compose down

# Remove containers AND volumes (deletes all data!)
docker-compose down -v

# Rebuild application image after code changes
docker-compose build app
docker-compose up -d app

# View all container statuses
docker-compose ps

# View logs for specific service
docker-compose logs -f app
docker-compose logs -f postgres
docker-compose logs -f neo4j
```

### Executing Commands Inside Containers

```powershell
# Open bash shell in app container
docker-compose exec app bash

# Run Python script
docker-compose exec app python scripts/inspect_relations.py

# Access PostgreSQL
docker-compose exec postgres psql -U postgres -d ats_db

# Access Neo4j Cypher Shell
docker-compose exec neo4j cypher-shell -u neo4j -p ats_neo4j_password

# Access Redis CLI
docker-compose exec redis redis-cli
```

### Data Management

```powershell
# List all volumes
docker volume ls

# Inspect a volume
docker volume inspect ats_postgres_data

# Backup PostgreSQL database
docker-compose exec postgres pg_dump -U postgres ats_db > backup.sql

# Restore PostgreSQL database
cat backup.sql | docker-compose exec -T postgres psql -U postgres -d ats_db

# Export Neo4j graph
docker-compose exec neo4j neo4j-admin database dump neo4j --to=/data/neo4j-backup.dump

# View ingestion state
docker-compose exec app cat /app/data/ingestion_state.json
```

### Development Workflow

```powershell
# 1. Edit code on your Windows machine (in api/, src/, scripts/)
# 2. Changes are automatically reflected (bind mounts)
# 3. For hot-reload, restart the app container:
docker-compose restart app

# After modifying requirements.txt:
docker-compose build app
docker-compose up -d app
```

## Troubleshooting

### Services Won't Start

```powershell
# Check service health
docker-compose ps

# View detailed logs
docker-compose logs --tail=50

# Restart specific service
docker-compose restart postgres
docker-compose restart neo4j
```

### Ollama Connection Issues

```powershell
# From app container, test Ollama connectivity
docker-compose exec app curl http://host.docker.internal:11434/api/tags

# Verify Ollama is running on host
ollama list

# Check if models are loaded
ollama ps
```

### Database Connection Errors

```powershell
# Verify PostgreSQL is accepting connections
docker-compose exec postgres pg_isready -U postgres

# Check Neo4j status
docker-compose exec neo4j neo4j status

# Review database logs
docker-compose logs postgres
docker-compose logs neo4j
```

### Port Conflicts

```powershell
# Check if ports are already in use
netstat -an | findstr "5432 7474 7687 8000"

# Stop conflicting services or modify ports in docker-compose.yml
```

### Volume Permission Issues

On Windows, ensure Docker Desktop has access to the drive where your project is located:

1. Docker Desktop → Settings → Resources → File Sharing
2. Add `D:\` (or your project drive)
3. Apply & Restart

### Out of Memory

```powershell
# Increase Docker memory allocation
# Docker Desktop → Settings → Resources → Memory
# Recommended: At least 8GB

# Check container resource usage
docker stats
```

### Reset Everything

```powershell
# WARNING: This deletes ALL data!
docker-compose down -v
docker system prune -a

# Then start fresh
docker-compose up -d
docker-compose exec app python scripts/init_db.py
```

## Environment Configuration

### Switching Between Local and Docker

- **Local development**: Use `.env` (localhost URLs)
- **Docker deployment**: Use `.env.docker` (container hostnames)

```powershell
# To use different env file
docker-compose --env-file .env.docker up -d
```

### Key Differences

| Variable        | Local (`.env`)           | Docker (`.env.docker`)              |
| --------------- | ------------------------ | ----------------------------------- |
| POSTGRES_HOST   | `localhost`              | `postgres`                          |
| NEO4J_URI       | `bolt://localhost:7687`  | `bolt://neo4j:7687`                 |
| OLLAMA_BASE_URL | `http://localhost:11434` | `http://host.docker.internal:11434` |

## Production Considerations

### Security Hardening

1. **Change default passwords** in `.env.docker`
2. **Use secrets management**: Docker secrets or external vault
3. **Enable TLS** for Neo4j and PostgreSQL
4. **Restrict network access**: Use Docker networks properly
5. **Run as non-root**: Already implemented in Dockerfile

### Scaling

```yaml
# In docker-compose.yml
app:
  deploy:
    replicas: 3
    resources:
      limits:
        cpus: "2"
        memory: 4G
```

### Monitoring

- Add health check endpoints monitoring
- Use Prometheus + Grafana for metrics
- Centralized logging with ELK stack

### Backup Strategy

1. **Database backups**: Daily automated dumps
2. **Volume snapshots**: Use Docker volume plugins
3. **Code versioning**: Git with proper tags
4. **Configuration backup**: Store `.env` files securely

## GPU Support (Advanced)

To use GPU for embeddings inside containers (Linux host only):

```yaml
# docker-compose.yml
app:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

**Note**: GPU passthrough is not well-supported on Windows Docker Desktop. Keep Ollama and embedding models on the host for best GPU performance.

## Next Steps

1. **Test API**: Open http://localhost:8000/docs
2. **Import Data**: Run ingestion on your resume dataset
3. **Monitor Logs**: Keep `docker-compose logs -f app` running
4. **Customize**: Adjust settings in `.env.docker` as needed
5. **Scale**: When ready, deploy to cloud with Docker Swarm or Kubernetes

## Support

- **Documentation**: See [README.md](README.md) for API usage
- **Issues**: Check logs with `docker-compose logs`
- **Health**: Monitor http://localhost:8000/health
