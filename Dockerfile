# Multi-stage Dockerfile for LightRAG ATS FastAPI Application
# Optimized for layer caching and minimal image size

# ============== Stage 1: Base Dependencies ==============
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# ============== Stage 2: Python Dependencies ==============
FROM base as dependencies

# Copy requirements if available, although we are manual here
COPY requirements.txt .

# Install PyTorch and core scientific packages FIRST
# Using a single RUN instruction for heavy packages to reduce layers
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch \
    sentence-transformers \
    numpy

# Install remaining application dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    lightrag-hku \
    asyncpg \
    neo4j \
    psycopg2-binary \
    pypdf \
    python-docx \
    httpx \
    aiohttp \
    pydantic-settings \
    python-dotenv \
    tqdm \
    tenacity \
    google-generativeai \
    rank-bm25 \
    rapidfuzz \
    pytest \
    pytest-asyncio \
    structlog \
    celery[redis] \
    redis

# ============== Stage 3: Application ==============
FROM dependencies as application

# Copy application code
COPY api/ /app/api/
COPY src/ /app/src/
COPY scripts/ /app/scripts/

# Create directories for runtime data
RUN mkdir -p /app/rag_storage /app/data/resumes

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
