"""
Configuration management for ATS system.
Uses Pydantic Settings for environment variable loading and validation.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # PostgreSQL Configuration
    postgres_uri: str = Field(
        default="postgresql+asyncpg://postgres:admin@localhost:5432/ats_db",
        description="PostgreSQL connection URI"
    )
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="admin")
    postgres_db: str = Field(default="ats_db")
    
    # Neo4j Configuration (use bolt:// for standalone, neo4j:// for cluster)
    neo4j_uri: str = Field(default="bolt://127.0.0.1:7687")
    neo4j_username: str = Field(default="neo4j")
    neo4j_password: str = Field(default="ats_neo4j_password")
    
    # Ollama / LLM Configuration
    ollama_base_url: str = Field(default="http://localhost:11434")
    
    llm_model: str = Field(default="llama3.1:8b")
    llm_extraction_model: str = Field(default="llama3.1:8b", description="Model for entity extraction (stronger for relationships)")
    llm_max_tokens: int = Field(default=4096)
    llm_temperature: float = Field(default=0.1)
    llm_timeout: float = Field(default=300.0, description="LLM request timeout in seconds (default: 5 minutes)")
    
    # Provider Selection
    llm_provider: str = Field(default="ollama", description="LLM provider: 'ollama', 'gemini', or 'runpod'")
    gemini_api_key: str = Field(default="", description="Google Gemini API Key")
    gemini_model: str = Field(default="gemini-flash-latest", description="Gemini model name")

    # RunPod Configuration
    runpod_api_key: str = Field(default="", description="RunPod API Key")
    runpod_endpoint_id: str = Field(default="", description="RunPod Serverless Endpoint ID")
    
    # OpenAI Configuration
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model name")
    
    # Embedding Configuration
    embedding_model: str = Field(default="BAAI/bge-m3")
    embedding_dim: int = Field(default=1024)
    embedding_max_tokens: int = Field(default=512)
    
    # Reranking Configuration
    rerank_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    # LightRAG Configuration
    rag_working_dir: str = Field(default="./rag_storage")
    chunk_token_size: int = Field(default=500)
    chunk_overlap_size: int = Field(default=50)
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_debug: bool = Field(default=True)
    
    # Logging
    log_level: str = Field(default="INFO")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience export
settings = get_settings()
