# Multi-stage Dockerfile for LightRAG ATS FastAPI Application
# Optimized for layer caching and minimal image size

# ============== Stage 1: Base Dependencies ==============
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

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

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download sentence-transformers models to cache them in the image
# This speeds up first-time startup
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('BAAI/bge-m3'); \
    SentenceTransformer('cross-encoder/ms-marco-MiniLM-L-6-v2')"

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
