# LightRAG ATS - Applicant Tracking System

Production-ready Applicant Tracking System with dual-level retrieval combining vector search and knowledge graph queries.

## Features

- **Dual-Level Retrieval**: Combines vector similarity search (PostgreSQL/pgvector) with knowledge graph traversal (Neo4j)
- **Status-Aware Ingestion**: Incremental processing with state tracking (skips unchanged files)
- **Adaptive Model Routing**: Uses Qwen 2.5 3B for high-speed extraction and Llama 3.1 8B for reasoning
- **5 Retrieval Modes**: naive, local, global, hybrid, mix - with automatic fallback
- **Resume Ingestion**: Supports PDF, DOCX, and TXT formats
- **Job-Based Analysis**: Shortlist candidates based on job descriptions
- **Conversational Chat**: AI-powered Q&A about candidates
- **Source Attribution**: Responses include context sources

## Tech Stack

| Component  | Technology                           |
| ---------- | ------------------------------------ |
| Backend    | FastAPI (Python 3.10+)               |
| RAG System | LightRAG                             |
| Vector DB  | PostgreSQL 16 + pgvector             |
| Graph DB   | Neo4j                                |
| LLM (Chat) | Ollama + Llama 3.1 8B                |
| LLM (Extr) | Ollama + Qwen 2.5 3B                 |
| Embeddings | BAAI/bge-m3 (1024 dim)               |
| Reranking  | cross-encoder/ms-marco-MiniLM-L-6-v2 |

## Quick Start

### 1. Prerequisites

- **OS**: Windows 10/11 (Project configured for Windows)
- **Python**: 3.10+
- **Docker & Docker Compose** (for Database containers)
- **Ollama**: Installed and running [Download Ollama](https://ollama.com/)
  - Required Models: `ollama pull llama3.1:8b` and `ollama pull qwen2.5:3b`
- **GPU (Optional but Recommended)**: NVIDIA GPU with CUDA support for faster embeddings

### 2. Automated Setup (Recommended)

Run the included setup script to checks requirements, create a virtual environment, and install dependencies:

```powershell
.\setup_env.bat
```

### 3. Start The System

1. **Start Databases**:

   ```powershell
   docker-compose up -d
   ```

2. **Initialize Database Schema** (First time only):

   ```powershell
   python -m venv venv
   ```

# OR if using a custom name: python -m venv venv312

.\venv\Scripts\activate

# OR: .\venv312\Scripts\activate

pip install -r requirements.txt

````

3. **Ingest Resumes**:

   ```powershell
   # Place resume files (PDF/DOCX/TXT) in data/resumes/
   # Standard run (Incremental - skips existing):
   .\venv\Scripts\python scripts/ingest_resumes.py --dir data/resumes --batch-size 5

   # Force re-ingestion of all files:
   .\venv\Scripts\python scripts/ingest_resumes.py --dir data/resumes --force
````

4. **Run API Server**:
   You can use the helper script:

   ```powershell
   .\run_api.bat
   ```

   Or manually:

   ```powershell
   cd api
   ..\venv\Scripts\uvicorn main:app --reload --port 8000
   ```

   **API Documentation**: http://localhost:8000/docs

## API Endpoints

### Ingestion

| Endpoint        | Method | Description                 |
| --------------- | ------ | --------------------------- |
| `/ingest`       | POST   | Upload single resume        |
| `/ingest/batch` | POST   | Batch ingest from directory |

### Analysis

| Endpoint            | Method | Description                     |
| ------------------- | ------ | ------------------------------- |
| `/analyze`          | POST   | Analyze job and find candidates |
| `/analyze/{job_id}` | GET    | Get stored analysis             |

### Chat

| Endpoint      | Method | Description                                |
| ------------- | ------ | ------------------------------------------ |
| `/chat/job`   | POST   | Chat about job candidates (dual retrieval) |
| `/chat/query` | POST   | Direct query without job context           |
| `/chat/modes` | GET    | Get available retrieval modes              |

### Health

| Endpoint  | Method | Description         |
| --------- | ------ | ------------------- |
| `/health` | GET    | System health check |
| `/stats`  | GET    | System statistics   |

## Usage Example

```python
import httpx

# 1. Analyze a job
response = httpx.post("http://localhost:8000/analyze", json={
    "query": "Senior Python developer with 5+ years experience",
    "job_id": "job-001",
    "top_k": 20
})
print(response.json())

# 2. Chat about candidates
response = httpx.post("http://localhost:8000/chat/job", json={
    "job_id": "job-001",
    "message": "Who has the most Python experience?",
    "mode": "mix"
})
print(response.json()["response"])
```

## Retrieval Modes

| Mode   | Description        | Speed   | Use Case                   |
| ------ | ------------------ | ------- | -------------------------- |
| naive  | Vector search only | Fastest | General search             |
| local  | Entity-specific    | Fast    | "Who has skill X?"         |
| global | Relationship-based | Medium  | Pattern analysis           |
| hybrid | Local + Global     | Medium  | Complex queries            |
| mix    | Full dual-level    | Slower  | Best results (recommended) |

## Project Structure

```
├── docker-compose.yml      # Database containers
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── src/                   # Core modules
│   ├── config.py          # Configuration
│   ├── llm_adapter.py     # Ollama integration
│   ├── embedding.py       # BGE-M3 embeddings
│   ├── reranker.py        # Cross-encoder
│   ├── rag_config.py      # LightRAG setup
│   ├── dual_retrieval.py  # Dual retrieval logic
│   ├── resume_parser.py   # PDF/DOCX parsing
│   └── ingestion.py       # Batch ingestion
├── api/                   # FastAPI application
│   ├── main.py            # Entry point
│   ├── models.py          # Pydantic schemas
│   ├── middleware.py      # Logging, CORS
│   └── routes/            # Endpoint handlers
├── scripts/               # CLI tools
│   ├── init_db.py         # Database init
│   ├── ingest_resumes.py  # Batch ingestion
│   └── test_retrieval.py  # Mode testing
├── tests/                 # Test suite
└── data/resumes/          # Resume files
```

## Running Tests

```powershell
python -m pytest tests/ -v
```

## Troubleshooting

### Port Conflicts

```powershell
# Check ports
netstat -an | findstr "5432 7474 7687"
```

### Database Connection

```powershell
# Verify containers
docker-compose ps
docker-compose logs postgres
```

### Ollama Issues

```powershell
# Check models
ollama list
# Pull required models
ollama pull llama3.1:8b
ollama pull qwen2.5:3b
```

## License

MIT License
