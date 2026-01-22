# LightRAG ATS - Applicant Tracking System

A production-ready Applicant Tracking System powered by **LightRAG** with intelligent dual-level retrieval combining vector search and knowledge graph traversal for superior candidate matching and analysis.

## 🌟 Key Features

### Core Capabilities

- **🧠 Dual-Level Retrieval**: Combines PostgreSQL/pgvector similarity search with Neo4j knowledge graph reasoning
- **📊 Smart Ingestion**: SHA-256 hash-based state tracking automatically skips unchanged resumes (incremental ingestion)
- **☁️ RunPod Serverless**: Optional offloading of LLM inference to RunPod GPU endpoints
- **🔀 Adaptive LLM Routing**:
  - `qwen2.5:3b` for fast entity extraction (Local or RunPod)
  - `llama3.1:8b` for complex reasoning (Local or RunPod)
- **🎯 5 Retrieval Modes**: naive, local, global, hybrid, mix - with intelligent fallback
- **📄 Multi-Format Support**: Ingest PDF, DOCX, and TXT resumes
- **💼 Job-Based Analysis**: AI-powered candidate shortlisting with relevance scoring
- **💬 Contextual Chat**: Job-aware conversational Q&A with source attribution
- **🔄 Entity Resolution**: Automatic skill and entity standardization for better graph connectivity

### Ingestion Intelligence

- File hash tracking in `data/ingestion_state.json`
- Automatic skip of unchanged resumes
- Batch processing with configurable concurrency
- Force re-ingestion flag for updates
- Progress tracking with detailed statistics

### Advanced Retrieval

- **Naive**: Pure vector similarity (fastest)
- **Local**: Entity-focused graph queries
- **Global**: Community-level pattern analysis
- **Hybrid**: Combined local + global reasoning
- **Mix**: Full dual-level retrieval (best quality)

## 🏗️ System Architecture

```mermaid
graph TB
    subgraph "Data Ingestion"
        A[Resume Files] --> B[Resume Parser]
        B --> C[LLM Extractor]
        C --> D[Entity Resolver]
        D --> E[LightRAG Pipeline]
    end

    subgraph "Storage Layer"
        E --> F[(PostgreSQL<br/>pgvector)]
        E --> G[(Neo4j<br/>Knowledge Graph)]
        H[Ingestion State<br/>JSON] -.tracks.-> A
    end

    subgraph "Retrieval Engine"
        I[User Query] --> J{Retrieval Mode}
        J -->|naive| K[Vector Search]
        J -->|local| L[Entity Graph]
        J -->|global| M[Community Graph]
        J -->|hybrid| N[Local + Global]
        J -->|mix| O[Dual-Level]
        J -->|mix| O[Dual-Level]

        K & L & M & N & O --> P[Reranker<br/>ms-marco-MiniLM]
    end

    subgraph "Response Generation"
        P --> Q[Context Builder]
        Q --> R{LLM Provider}
        R -->|Local| S[Ollama]
        R -->|Cloud| T[RunPod / Gemini]
        S & T --> U[Structured Response]
    end

    F & G -.data.-> K & L & M & N & O
```

## 🛠️ Tech Stack

| Component          | Technology                           | Purpose                               |
| ------------------ | ------------------------------------ | ------------------------------------- |
| **Backend**        | FastAPI (Python 3.10+)               | REST API server                       |
| **RAG Framework**  | LightRAG                             | Document processing & retrieval       |
| **Vector Store**   | PostgreSQL 16 + pgvector             | Embedding storage & similarity search |
| **Graph Database** | Neo4j Community                      | Knowledge graph & relationships       |
| **LLM Inference**  | Ollama / RunPod Serverless           | Entity extraction & Reasoning         |
| **Embeddings**     | BAAI/bge-m3 (1024-dim)               | Semantic text representation          |
| **Reranking**      | cross-encoder/ms-marco-MiniLM-L-6-v2 | Result refinement                     |
| **Parsing**        | PyPDF2, python-docx                  | Resume text extraction                |

## 🚀 Quick Start

### Prerequisites

- **OS**: Windows 10/11 (currently configured for Windows)
- **Python**: 3.10 or higher (for local development)
- **Docker Desktop**: For containerized deployment or database services
- **Ollama**: Required for local LLM inference (Optional if using RunPod)
- **GPU**: Optional but recommended (NVIDIA with CUDA support for faster embeddings)

### Deployment Options

You can run the ATS system in two ways:

#### Option 1: 🐳 Docker (Recommended for Production)

**Advantages**: Consistent environment, easy deployment, no dependency conflicts

```powershell
# Quick start - runs everything in containers
.\docker-start.bat

# Then initialize and ingest
docker-compose exec app python scripts/init_db.py
docker-compose exec app python scripts/ingest_resumes.py --dir /app/data/resumes --batch-size 5
```

**Access**:

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474

**Note**: Ollama runs on your host machine for optimal GPU access. See [DOCKER.md](DOCKER.md) for complete guide.

#### Option 2: 💻 Local Development

**Advantages**: Direct code editing, easier debugging, full control

Continue with the installation section below for local setup.

---

## 🐳 Docker Deployment (Quick Reference)

For complete Docker documentation, see **[DOCKER.md](DOCKER.md)**.

### Quick Commands

```powershell
# Start all services (app, postgres, neo4j, redis)
docker-compose up -d

# View logs
docker-compose logs -f app

# Initialize database
docker-compose exec app python scripts/init_db.py

# Ingest resumes
docker-compose exec app python scripts/ingest_resumes.py --dir /app/data/resumes --batch-size 5

# Stop services
docker-compose stop

# Remove containers (keeps data)
docker-compose down
```

### Architecture

All services run in separate containers:

- **app**: FastAPI application
- **postgres**: PostgreSQL + pgvector for vector storage
- **neo4j**: Knowledge graph database
- **redis**: Caching layer
- **Ollama**: Runs on host machine (or external RunPod endpoint)

For detailed documentation, troubleshooting, and advanced configuration, see **[DOCKER.md](DOCKER.md)**.

---

## 💻 Local Development Installation

#### 1. Clone and Setup Environment

```powershell
# Automated setup (recommended)
.\setup_env.bat
```

This script will:

- ✅ Check Python version
- ✅ Create virtual environment
- ✅ Install all dependencies
- ✅ Verify Ollama installation
- ✅ Pull required LLM models

#### 2. Configure Environment

```powershell
# Copy environment template
copy .env.example .env

# Edit .env with your settings (see below)
```

Key configuration options:

```env
# LLM Provider Selection
LLM_PROVIDER=ollama            # Options: ollama, runpod, gemini

# LLM Models
LLM_MODEL=llama3.1:8b          # Chat/reasoning model
LLM_EXTRACTION_MODEL=qwen2.5:3b # Fast extraction model

# RunPod Configuration (Optional)
RUNPOD_API_KEY=your_key...
RUNPOD_ENDPOINT_ID=your_id...

# Database (default localhost)
POSTGRES_URI=postgresql+asyncpg://postgres:ats_secure_password@localhost:5432/ats_db
NEO4J_URI=bolt://localhost:7687
```

#### 3. Start Databases

```powershell
# Start PostgreSQL and Neo4j containers
docker-compose up -d

# Verify containers are running
docker-compose ps
```

#### 4. Initialize Database Schema

```powershell
# Activate virtual environment
.\venv\Scripts\activate

# Initialize database tables
python scripts/init_db.py
```

#### 5. Ingest Resumes

```powershell
# Place resume files in data/resumes/

# Run incremental ingestion (skips already-ingested files)
python scripts/ingest_resumes.py --dir data/resumes --batch-size 5

# Force re-ingest all files (ignores state tracking)
python scripts/ingest_resumes.py --dir data/resumes --force --batch-size 5
```

**Ingestion Features**:

- 📁 Automatic file discovery (PDF, DOCX, TXT)
- 🔐 SHA-256 hash tracking (detects file changes)
- ⚡ Batch processing with configurable concurrency
- 📊 Progress tracking with statistics
- 💾 State persistence in `data/ingestion_state.json`

#### 6. Start API Server

```powershell
# Use helper script
.\run_api.bat

# Or manually
cd api
..\venv\Scripts\uvicorn main:app --reload --port 8000
```

🎉 **API is now running at**: http://localhost:8000  
📚 **Interactive docs**: http://localhost:8000/docs

## 📡 API Reference

### Health & Status

#### `GET /health`

System health check

**Response**:

```json
{
  "status": "healthy",
  "rag_initialized": true,
  "timestamp": "2025-12-21T07:30:00"
}
```

#### `GET /stats`

System statistics

**Response**:

```json
{
  "total_documents": 65,
  "total_entities": 1250,
  "total_relationships": 3400,
  "storage_backend": "dual"
}
```

### Ingestion

#### `POST /ingest`

Upload and ingest a single resume

**Request**:

```json
{
  "file": "<multipart/form-data>",
  "metadata": {
    "source": "linkedin",
    "tags": ["software-engineer"]
  }
}
```

#### `POST /ingest/batch`

Batch ingest from directory

**Request**:

```json
{
  "directory": "data/resumes",
  "batch_size": 5,
  "force": false
}
```

### Analysis

#### `POST /analyze`

Analyze job requirements and retrieve matching candidates

**Request**:

```json
{
  "query": "Senior Python developer with 5+ years of experience in Django and React",
  "job_id": "job-2024-001",
  "top_k": 20,
  "mode": "mix"
}
```

**Response**:

```json
{
  "job_id": "job-2024-001",
  "candidates": [
    {
      "name": "Michael Chen",
      "relevance_score": 0.92,
      "summary": "8 years Python, Django expert, React proficiency",
      "matching_skills": ["Python", "Django", "React", "PostgreSQL"],
      "source_chunks": ["Resume: Michael Chen..."]
    }
  ],
  "total_candidates": 15,
  "mode_used": "mix"
}
```

#### `GET /analyze/{job_id}`

Retrieve previously stored analysis results

### Chat

#### `POST /chat/job`

Contextual chat about candidates for a specific job

**Request**:

```json
{
  "job_id": "job-2024-001",
  "message": "Who has the most Python experience?",
  "mode": "mix"
}
```

**Response**:

```json
{
  "response": "Based on the shortlisted candidates, Michael Chen has the most Python experience with 8 years of professional work...",
  "sources": ["Resume: Michael Chen", "Resume: Sarah Johnson"],
  "mode": "mix"
}
```

#### `POST /chat/query`

Direct query across all candidates (no job context)

**Request**:

```json
{
  "query": "Find all candidates with AWS certification",
  "mode": "local"
}
```

#### `GET /chat/modes`

List available retrieval modes

**Response**:

```json
{
  "modes": ["naive", "local", "global", "hybrid", "mix"],
  "default": "mix"
}
```

## 🎯 Retrieval Modes Explained

| Mode       | Strategy                         | Speed      | Best For                   | Example Query                  |
| ---------- | -------------------------------- | ---------- | -------------------------- | ------------------------------ |
| **naive**  | Vector similarity only           | ⚡ Fastest | General keyword search     | "Python developer"             |
| **local**  | Entity + local graph             | ⚡ Fast    | Specific skills/attributes | "Who has AWS certification?"   |
| **global** | Community-level patterns         | 🐢 Medium  | Broad relationships        | "Similar candidates to X"      |
| **hybrid** | Local + Global combined          | 🐢 Medium  | Complex multi-criteria     | "Senior engineer + leadership" |
| **mix**    | Full dual-level (vector + graph) | 🐢 Slower  | Highest quality results    | Job matching, deep analysis    |

**💡 Recommendation**: Use `mix` mode for job analysis and important queries. Use `naive` or `local` for quick lookups.

## 📁 Project Structure

```
d:/ATS-Share/
├── api/                           # FastAPI application
│   ├── main.py                   # App entry point, middleware
│   ├── models.py                 # Pydantic schemas
│   ├── middleware.py             # Logging, CORS, error handling
│   └── routes/
│       ├── analyze.py            # Job analysis endpoints
│       ├── chat.py               # Chat & query endpoints
│       └── ingest.py             # Ingestion endpoints
│
├── src/                          # Core business logic
│   ├── config.py                 # Environment configuration
│   ├── rag_config.py             # LightRAG initialization
│   ├── llm_adapter.py            # Ollama integration
│   ├── embedding.py              # BGE-M3 embedding model
│   ├── reranker.py               # Cross-encoder reranking
│   ├── dual_retrieval.py         # Dual-level retrieval logic
│   ├── entity_resolver.py        # Skill/entity standardization
│   ├── resume_parser.py          # PDF/DOCX/TXT parsing
│   ├── prompts.py                # LLM prompt templates
│   ├── logging_config.py         # Structured logging
│   └── services/
│       └── ingestion_service.py  # Batch ingestion with state tracking
│
├── scripts/                      # CLI utilities
│   ├── init_db.py                # Database schema initialization
│   ├── ingest_resumes.py         # Batch resume ingestion CLI
│   └── inspect_relations.py      # Graph relationship inspector
│
├── data/
│   ├── resumes/                  # Resume file storage
│   ├── ingestion_state.json      # File hash tracking
│   └── golden_set.json           # Test/validation data
│
├── rag_storage/                  # LightRAG working directory
│   ├── vdb_entities.json         # Entity vector storage
│   ├── kv_store_llm_response_cache.json
│   └── graph_chunk_entity_relation.graphml
│
├── tests/                        # Test suite
├── docs/                         # Additional documentation
├── docker-compose.yml            # PostgreSQL + Neo4j
├── requirements.txt              # Python dependencies
├── .env.example                  # Configuration template
├── setup_env.bat                 # Automated setup script
└── run_api.bat                   # API server launcher
```

## 🔧 Advanced Configuration

### Ingestion Tuning

```python
# In src/rag_config.py
CHUNK_TOKEN_SIZE = 1200        # Larger = more context per chunk
CHUNK_OVERLAP_SIZE = 200       # Overlap prevents info loss
```

### LLM Selection

```env
# .env file
LLM_MODEL=llama3.1:8b           # Reasoning (accuracy-focused)
LLM_EXTRACTION_MODEL=qwen2.5:3b # Extraction (speed-focused)
LLM_TEMPERATURE=0.1             # Lower = more deterministic
```

### Batch Processing

```powershell
# Increase concurrency for faster ingestion
python scripts/ingest_resumes.py --dir data/resumes --batch-size 10
```

### GPU Acceleration

The system automatically uses GPU if available for:

- Embedding generation (via `sentence-transformers`)
- Reranking (via `cross-encoder`)

Verify GPU usage:

```powershell
python src/check_cuda.py
```

## 🧪 Testing

```powershell
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_ingestion.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

Manual verification scripts:

```powershell
# Test chat with job context
python test_chat_fix.py

# Verify ingestion and querying
python test_verification.py

# Inspect graph relationships
python scripts/inspect_relations.py
```

## 📊 Monitoring & Debugging

### Check Ingestion State

```powershell
# View ingestion state
type data\ingestion_state.json

# Count ingested files
python -c "import json; print(len(json.load(open('data/ingestion_state.json'))))"
```

### Database Inspection

```powershell
# PostgreSQL
docker exec -it ats-postgres psql -U postgres -d ats_db
# \dt - list tables
# SELECT COUNT(*) FROM documents;

# Neo4j Browser
# Open http://localhost:7474
# Query: MATCH (n) RETURN count(n)
```

### Logs

```powershell
# API logs (if running via uvicorn)
# Check console output

# Docker logs
docker-compose logs postgres
docker-compose logs neo4j
```

## ❗ Troubleshooting

### Port Conflicts

```powershell
# Check if ports are in use
netstat -an | findstr "5432 7474 7687 8000 11434"

# Kill process on port (example for 8000)
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Database Connection Issues

```powershell
# Restart containers
docker-compose down
docker-compose up -d

# Check container health
docker-compose ps
docker-compose logs
```

### Ollama Model Issues

```powershell
# List installed models
ollama list

# Pull missing models
ollama pull llama3.1:8b
ollama pull qwen2.5:3b

# Test model
ollama run llama3.1:8b "Hello"
```

### Ingestion State Reset

```powershell
# Backup current state
copy data\ingestion_state.json data\ingestion_state_backup.json

# Reset state (forces full re-ingestion)
echo {} > data\ingestion_state.json
```

### Empty Query Results

1. **Verify data is ingested**:

   ```powershell
   python -c "import json; print(len(json.load(open('data/ingestion_state.json'))))"
   ```

2. **Check RAG storage**:

   ```powershell
   dir rag_storage
   ```

3. **Try different retrieval mode**:
   ```python
   # Start with naive mode, then try mix
   {"mode": "naive"}  # vs {"mode": "mix"}
   ```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

---

**Built with ❤️ using LightRAG, FastAPI, and Ollama**
