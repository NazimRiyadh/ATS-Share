# Scripts Directory

This directory contains various scripts for managing the ATS system.

## Production Scripts

These scripts are for regular system operations:

- **`ingest_resumes.py`** - Batch ingest resumes from a directory

  ```bash
  python scripts/ingest_resumes.py --dir ./data/resumes --batch-size 5
  ```

- **`init_db.py`** - Initialize database schema (PostgreSQL + Neo4j)

  ```bash
  python scripts/init_db.py
  ```

- **`reset_db.py`** - Reset all databases (⚠️ destructive!)
  ```bash
  python scripts/reset_db.py
  ```

## Development & Debugging Scripts

- **`inspect_db.py`** - View database contents and statistics
- **`inspect_relations.py`** - Inspect Neo4j relationships
- **`debug_llm_extraction.py`** - Debug LLM entity extraction
- **`debug_splitter.py`** - Debug document chunking
- **`check_neo4j_count.py`** - Count nodes/relationships in Neo4j

## Evaluation & Testing Scripts

- **`evaluate_rag.py`** - Evaluate RAG retrieval accuracy
- **`evaluate_deployment.py`** - Full system evaluation
- **`benchmark_system.py`** - Performance benchmarks
- **`stress_test.py`** - Load testing
- **`test_async_ingest.py`** - Test async ingestion
- **`test_ingest_one.py`** - Test single resume ingestion
- **`test_rag_query.py`** - Test RAG queries
- **`test_retrieval.py`** - Test retrieval modes

## Data Management Scripts

- **`download_resumes.py`** - Download sample resume dataset
- **`populate_resumes_with_names.py`** - Add candidate names to database
- **`cleanup_unknown.py`** - Remove "Unknown Candidate" entries
- **`rebuild_graph.py`** - Rebuild Neo4j knowledge graph
- **`export_embeddings.py`** - Export embeddings for visualization

## Database Setup

- **`setup_postgres.sql`** - PostgreSQL schema (for reference)
- **`db_setup_docker.py`** - Setup databases in Docker

## Usage Examples

```bash
# Activate virtual environment
.\venv\Scripts\activate

# Initialize fresh database
python scripts/init_db.py

# Ingest all resumes
python scripts/ingest_resumes.py --dir ./data/resumes

# Inspect what was ingested
python scripts/inspect_db.py

# Run evaluation
python scripts/evaluate_rag.py
```

## Notes

- Most scripts require the virtual environment to be activated
- Database connection settings are read from `.env` file
- Some scripts may take several minutes to complete (ingestion, evaluation)
