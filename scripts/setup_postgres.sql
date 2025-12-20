-- LightRAG PostgreSQL Schema Setup
-- Run this script in your PostgreSQL database to create required tables

-- STEP 1: Docker automatically creates 'ats_db'
-- So we just need to run the table creation on 'ats_db'

-- STEP 2: Connect to ats_db database and run the rest:

-- Enable pgvector extension (required for vector similarity search)
CREATE EXTENSION IF NOT EXISTS vector;

-- DROP existing tables to ensure clean schema (RESET)
DROP TABLE IF EXISTS LIGHTRAG_DOC_FULL CASCADE;
DROP TABLE IF EXISTS LIGHTRAG_DOC_CHUNKS CASCADE;
DROP TABLE IF EXISTS LIGHTRAG_VDB_ENTITY CASCADE;
DROP TABLE IF EXISTS LIGHTRAG_VDB_RELATION CASCADE;
DROP TABLE IF EXISTS LIGHTRAG_LLM_CACHE CASCADE;
DROP TABLE IF EXISTS LIGHTRAG_DOC_STATUS CASCADE;

-- 1. Document Full Text Storage
CREATE TABLE IF NOT EXISTS LIGHTRAG_DOC_FULL (
    id VARCHAR(255),
    workspace VARCHAR(255),
    doc_name VARCHAR(255),
    content TEXT,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP,
    CONSTRAINT LIGHTRAG_DOC_FULL_PK PRIMARY KEY (workspace, id)
);

-- 2. Document Chunks Storage (with vectors)
CREATE TABLE IF NOT EXISTS LIGHTRAG_DOC_CHUNKS (
    id VARCHAR(255),
    workspace VARCHAR(255),
    full_doc_id VARCHAR(256),
    chunk_order_index INTEGER,
    tokens INTEGER,
    content TEXT,
    content_vector VECTOR(1024),  -- 1024-dim for bge-m3
    file_path VARCHAR(256),
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP,
    CONSTRAINT LIGHTRAG_DOC_CHUNKS_PK PRIMARY KEY (workspace, id)
);

-- 3. Entity Vector Storage
CREATE TABLE IF NOT EXISTS LIGHTRAG_VDB_ENTITY (
    id VARCHAR(255),
    workspace VARCHAR(255),
    entity_name VARCHAR(255),
    content TEXT,
    content_vector VECTOR(1024),
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP,
    chunk_ids VARCHAR(255)[] NULL,
    file_path TEXT NULL,
    CONSTRAINT LIGHTRAG_VDB_ENTITY_PK PRIMARY KEY (workspace, id)
);

-- 4. Relationship Vector Storage
CREATE TABLE IF NOT EXISTS LIGHTRAG_VDB_RELATION (
    id VARCHAR(255),
    workspace VARCHAR(255),
    source_id VARCHAR(256),
    target_id VARCHAR(256),
    content TEXT,
    content_vector VECTOR(1024),
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP,
    chunk_ids VARCHAR(255)[] NULL,
    file_path TEXT NULL,
    CONSTRAINT LIGHTRAG_VDB_RELATION_PK PRIMARY KEY (workspace, id)
);

-- 5. LLM Response Cache
CREATE TABLE IF NOT EXISTS LIGHTRAG_LLM_CACHE (
    workspace VARCHAR(255) NOT NULL,
    id VARCHAR(255) NOT NULL,
    mode VARCHAR(32) NOT NULL,
    original_prompt TEXT,
    return_value TEXT,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP,
    CONSTRAINT LIGHTRAG_LLM_CACHE_PK PRIMARY KEY (workspace, mode, id)
);

-- 6. Document Processing Status
CREATE TABLE IF NOT EXISTS LIGHTRAG_DOC_STATUS (
    workspace VARCHAR(255) NOT NULL,
    id VARCHAR(255) NOT NULL,
    content TEXT NULL,
    content_summary VARCHAR(255) NULL,
    content_length INT NULL,
    chunks_count INT NULL,
    status VARCHAR(64) NULL,
    file_path TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    CONSTRAINT LIGHTRAG_DOC_STATUS_PK PRIMARY KEY (workspace, id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_lightrag_doc_full_id ON LIGHTRAG_DOC_FULL(id);
CREATE INDEX IF NOT EXISTS idx_lightrag_doc_chunks_id ON LIGHTRAG_DOC_CHUNKS(id);
CREATE INDEX IF NOT EXISTS idx_lightrag_vdb_entity_id ON LIGHTRAG_VDB_ENTITY(id);
CREATE INDEX IF NOT EXISTS idx_lightrag_vdb_relation_id ON LIGHTRAG_VDB_RELATION(id);
CREATE INDEX IF NOT EXISTS idx_lightrag_llm_cache_id ON LIGHTRAG_LLM_CACHE(id);
CREATE INDEX IF NOT EXISTS idx_lightrag_doc_status_id ON LIGHTRAG_DOC_STATUS(id);

-- Create vector indexes for similarity search (using IVFFlat)
CREATE INDEX IF NOT EXISTS idx_lightrag_doc_chunks_vector ON LIGHTRAG_DOC_CHUNKS USING ivfflat (content_vector vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_lightrag_vdb_entity_vector ON LIGHTRAG_VDB_ENTITY USING ivfflat (content_vector vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_lightrag_vdb_relation_vector ON LIGHTRAG_VDB_RELATION USING ivfflat (content_vector vector_cosine_ops);


-- 7. Key-Value Storage (General purpose, including pipeline status)
CREATE TABLE IF NOT EXISTS LIGHTRAG_KV_STORE (
    workspace VARCHAR(255) NOT NULL,
    key VARCHAR(255) NOT NULL,
    value TEXT,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP,
    CONSTRAINT LIGHTRAG_KV_STORE_PK PRIMARY KEY (workspace, key)
);

CREATE INDEX IF NOT EXISTS idx_lightrag_kv_store_key ON LIGHTRAG_KV_STORE(key);

SELECT 'LightRAG schema created successfully!' AS result;
