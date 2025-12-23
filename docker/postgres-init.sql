-- PostgreSQL Initialization Script for LightRAG ATS
-- This script runs automatically when the container is first created

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Log successful initialization
DO $$
BEGIN
  RAISE NOTICE 'pgvector extension enabled successfully';
END
$$;
