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

# Copy only requirements first for better caching
COPY requirements.txt .

# Install heavy dependencies FIRST as separate layer (PyTorch ~900MB)
# This layer will be cached and won't need to re-download unless PyTorch version changes
RUN pip install --no-cache-dir --timeout=300 \
    torch>=2.1.0 \
    sentence-transformers>=2.2.2

# Install FastAPI and web framework
RUN pip install --no-cache-dir --timeout=300 \
    fastapi>=0.109.0 \
    uvicorn[standard]>=0.27.0 \
    python-multipart>=0.0.6

# Install database drivers
RUN pip install --no-cache-dir --timeout=300 \
    lightrag-hku>=1.0.0 \
    asyncpg>=0.29.0 \
    neo4j>=5.15.0 \
    psycopg2-binary>=2.9.9

# Install remaining dependencies (adding new packages here won't invalidate PyTorch cache)
RUN pip install --no-cache-dir --timeout=300 \
    pypdf>=3.17.0 \
    python-docx>=1.1.0 \
    httpx>=0.26.0 \
    aiohttp>=3.9.0 \
    pydantic-settings>=2.1.0 \
    python-dotenv>=1.0.0 \
    tqdm>=4.66.0 \
    tenacity>=8.2.3 \
    google-generativeai>=0.3.2 \
    rank-bm25>=0.2.2 \
    rapidfuzz>=3.6.0 \
    pytest>=7.4.0 \
    pytest-asyncio>=0.23.0 \
    structlog>=24.1.0

# Note: PyTorch is installed first in its own layer
# Adding new packages to the last RUN won't force PyTorch re-download

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
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
