"""
LightRAG configuration and initialization.
Sets up LightRAG with PostgreSQL vector storage and Neo4j graph storage.
"""

import os
import logging
import json
from typing import Optional

from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc

from .config import settings
from .llm_adapter import ollama_llm_func
from .embedding import embedding_func, get_embedding_model
from .reranker import rerank_func
from .prompts import ATS_ENTITY_EXTRACTION_PROMPT
try:
    from lightrag.kg.shared_storage import initialize_pipeline_status
except ImportError:
    initialize_pipeline_status = None

# Monkey patch for DocProcessingStatus error/error_msg mismatch
try:
    from lightrag.base import DocProcessingStatus
    import dataclasses
    
    _original_init = DocProcessingStatus.__init__
    _valid_fields = {f.name for f in dataclasses.fields(DocProcessingStatus)}
    
    def _new_init(self, *args, **kwargs):
        if 'error' in kwargs:
            kwargs['error_msg'] = kwargs.pop('error')
            
        # Filter unknown arguments
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in _valid_fields}
        
        _original_init(self, *args, **filtered_kwargs)
        
    DocProcessingStatus.__init__ = _new_init
    print("Applied DocProcessingStatus monkey patch (robust)")
except ImportError:
    pass

# Monkey patch for LightRAG.__init__ to fix _storage_lock race condition
try:
    import asyncio
    
    # Store original init if not already patched (basic check)
    if not getattr(LightRAG, "_lock_patched", False):
        _original_lightrag_init = LightRAG.__init__
        
        def _new_lightrag_init(self, *args, **kwargs):
            _original_lightrag_init(self, *args, **kwargs)
            # Force initialize lock if it's missing or None
            if not hasattr(self, '_storage_lock') or self._storage_lock is None:
                self._storage_lock = asyncio.Lock()
        
        LightRAG.__init__ = _new_lightrag_init
        setattr(LightRAG, "_lock_patched", True)
        print("Applied LightRAG._storage_lock monkey patch (robust)")
except Exception as e:
    print(f"Failed to apply LightRAG lock patch: {e}")

from src.logging_config import get_logger

logger = get_logger(__name__)


def _setup_environment():
    """Set environment variables for LightRAG storage backends."""
    # Neo4j configuration via environment variables
    os.environ["NEO4J_URI"] = settings.neo4j_uri
    os.environ["NEO4J_USERNAME"] = settings.neo4j_username
    os.environ["NEO4J_PASSWORD"] = settings.neo4j_password
    
    # PostgreSQL configuration
    os.environ["POSTGRES_HOST"] = settings.postgres_host
    os.environ["POSTGRES_PORT"] = str(settings.postgres_port)
    os.environ["POSTGRES_USER"] = settings.postgres_user
    os.environ["POSTGRES_PASSWORD"] = settings.postgres_password
    os.environ["POSTGRES_DATABASE"] = settings.postgres_db
    
    # Force Neo4j to use default database (Community Edition support)
    os.environ["NEO4J_DATABASE"] = "neo4j"


class RAGManager:
    """Manages LightRAG instance lifecycle."""
    
    def __init__(self):
        self._rag: Optional[LightRAG] = None
        self._initialized = False
    
    async def initialize(self) -> LightRAG:
        """Initialize LightRAG with dual storage configuration."""
        if self._initialized and self._rag is not None:
            return self._rag
        
        logger.info("Initializing LightRAG...")
        
        # Ensure working directory exists
        os.makedirs(settings.rag_working_dir, exist_ok=True)
        
        # Create embedding function wrapper for LightRAG
        embedding_model = get_embedding_model()
        
        async def _embedding_func(texts):
            """Wrapper to match LightRAG's expected signature."""
            return await embedding_func(texts)
        
        try:
            # Set up environment variables for database connections
            _setup_environment()
            
            # CRITICAL: Define strict Entity Types for ATS Domain
            # This aligns with the prompt in src/prompts.py
            os.environ["ENTITY_TYPES"] = json.dumps([
                "PERSON", "SKILL", "ROLE", "COMPANY", 
                "CERTIFICATION", "LOCATION", "EDUCATION", 
                "PROJECT", "INDUSTRY"
            ])
            logger.info("Configured ATS Entity Types")
            
            # Initialize LightRAG with PostgreSQL (vectors) and Neo4j (graph)
            self._rag = LightRAG(
                working_dir=settings.rag_working_dir,
                
                # LLM Configuration (Ollama)
                llm_model_func=ollama_llm_func,

                # Embedding Configuration
                embedding_func=EmbeddingFunc(
                    embedding_dim=settings.embedding_dim,
                    max_token_size=settings.embedding_max_tokens,
                    func=_embedding_func
                ),
                
                # Reranking Configuration
                # rerank_model_func=rerank_func,  # REMOVED: Not supported in this LightRAG version
                
                # Storage Configuration - Use PostgreSQL and Neo4j
                kv_storage="PGKVStorage",                    # PostgreSQL for key-value
                vector_storage="PGVectorStorage",            # PostgreSQL + pgvector for vectors
                graph_storage="Neo4JStorage",                # Neo4j for knowledge graph
                
                # Chunking Configuration
                chunk_token_size=settings.chunk_token_size,
                chunk_overlap_token_size=settings.chunk_overlap_size,
                
                # Force Doc Status to Postgres
                doc_status_storage="PGDocStatusStorage",
            )
            
            # Monkey Patch: Inject custom prompt and delimiters for Llama 3.1
            # We modify the global PROMPTS dictionary which extract_entities reads
            try:
                from lightrag.prompt import PROMPTS
                
                # Override the entity extraction prompt with ATS-specific version
                # Correct key for LightRAG 1.4.9.8 is "entity_extraction_system_prompt"
                PROMPTS["entity_extraction_system_prompt"] = ATS_ENTITY_EXTRACTION_PROMPT
                PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "###"
                PROMPTS["DEFAULT_RECORD_DELIMITER"] = "\n"
                PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "\n\n"
                
                # CRITICAL: Override examples to use correct delimiter format for LightRAG parser
                PROMPTS["entity_extraction_examples"] = [
                    """entity###John Doe###PERSON###Candidate name
entity###Python###SKILL###Programming language
entity###Senior Data Analyst###ROLE###Job title
entity###Google###COMPANY###Technology company
entity###San Francisco###LOCATION###City in California
entity###AWS Certified###CERTIFICATION###Cloud certification
relationship###John Doe###HAS_SKILL###Python###Listed in skills section
relationship###John Doe###HAS_ROLE###Senior Data Analyst###Current position
relationship###John Doe###WORKED_AT###Google###Employment history
relationship###John Doe###LOCATED_IN###San Francisco###Resume header
relationship###John Doe###HAS_CERTIFICATION###AWS Certified###Certifications section"""
                ]
                
                print("Applied PROMPTS monkey patch for Llama 3.1 format")
                
                # ==========================================
                # Monkey Patch 3: Robust Parser for Llama 3.1
                # ==========================================
                import lightrag.utils

                def robust_split_string_by_multi_markers(content: str, markers: list[str], item_fallback: bool = False):
                    """
                    Robust splitting function that handles mismatched field counts.
                    Original raises 'found X/Y fields' error.
                    This version pads missing fields or merges extra fields.
                    AND performs Entity Resolution (cleaning/standardization).
                    """
                    if not markers:
                        return [content.strip()]
                    
                    results = [content]
                    for marker in markers:
                        new_results = []
                        for r in results:
                            new_results.extend(r.split(marker))
                        results = new_results
                    
                    results = [r.strip() for r in results if r.strip()]
                    
                    if not results:
                        return []
                        
                    # Normalize first token to check type (safely ignore quotes/parens)
                    first_token = results[0].lower().strip('("')
    
                    # ---------------------------------------------------------
                    # SMART FIX 1: Auto-correct mislabeled relationships
                    # LLM sometimes outputs ("entity"###Src###REL###Tgt###Desc)
                    # which is actually a relationship with wrong label
                    # ---------------------------------------------------------
                    if len(results) >= 5 and "entity" in first_token:
                        results[0] = results[0].lower().replace("entity", "relationship")
                        first_token = "relationship"

                    # ---------------------------------------------------------
                    # SMART FIX 2: Enforce strict field counts (Truncate/Pad)
                    # ---------------------------------------------------------
                    if "entity" in first_token:
                        # Expected: ("entity", Name, Type, Description) -> 4 fields
                        if len(results) > 4:
                            results = results[:4]  # Truncate extra fields
                        elif len(results) < 4:
                            missing = 4 - len(results)
                            # results is ["entity", Name, Type, Description]
                            # If we have 3 items: ["entity", Name, Type] -> add Desc
                            # If we have 2 items: ["entity", Name] -> add Type, Desc
                            if missing == 1:
                                results.append("Description not provided")
                            else:
                                # Start filling from Type index (2)
                                start_fill = 4 - missing
                                for idx in range(start_fill, 4):
                                    if idx == 2: # Type
                                        results.append("UNKNOWN")
                                    else: # Description
                                        results.append("Description not provided")
                            
                    elif "relationship" in first_token:
                        # Expected: ("relationship", Src, Rel, Tgt, Desc) -> 5 fields
                        if len(results) > 5:
                            results = results[:5]  # Truncate extra fields
                        elif len(results) < 5:
                            missing = 5 - len(results)
                            results.extend(["Evidence not provided"] * missing)

                    # =========================================================
                    # ENTITY RESOLUTION INTEGRATION
                    # =========================================================
                    # Valid canonical entity types
                    VALID_ENTITY_TYPES = {'PERSON', 'SKILL', 'COMPANY', 'ROLE', 'LOCATION', 
                                         'CERTIFICATION', 'EDUCATION', 'PROJECT', 'INDUSTRY'}
                    
                    try:
                        # Lazy import to avoid circular dependencies if any
                        from src.entity_resolver import get_entity_resolver
                        resolver = get_entity_resolver()
                        
                        if "entity" in first_token and len(results) >= 3:
                            # Format: ("entity", Name, Type, Description)
                            entity_name = results[1]
                            entity_type = results[2].upper().strip()
                            
                            # CRITICAL: Reject entities with invalid types
                            if entity_type not in VALID_ENTITY_TYPES:
                                # Skip this entity entirely by returning empty
                                return []
                            
                            # Update type to uppercase canonical form
                            results[2] = entity_type
                            
                            resolved = resolver.resolve_entity(entity_name, entity_type)
                            results[1] = resolved.canonical
                            
                        elif "relationship" in first_token and len(results) >= 3:
                            # Format: ("relationship", Src, RelType, Tgt, Desc)
                            rel_type = results[2]
                            is_valid, canonical_type = resolver.validate_relationship_type(rel_type)
                            results[2] = canonical_type
                            
                            # Also resolve source/target names if possible? 
                            # Ideally yes, but we don't know their types easily here.
                            # For now, just clean the names basic
                            results[1] = resolver._clean_entity_name(results[1])
                            if len(results) > 3:
                                results[3] = resolver._clean_entity_name(results[3])
                                
                    except Exception as e:
                        # Fail safe - don't stop ingestion if resolution crashes
                        pass

                    return results

                # Overwrite the utility function directly in utils
                lightrag.utils.split_string_by_multi_markers = robust_split_string_by_multi_markers
                
                # Also overwrite in operate module if it was imported directly
                try:
                    import lightrag.operate
                    lightrag.operate.split_string_by_multi_markers = robust_split_string_by_multi_markers
                    logger.info("Applied Robust Parser monkey patch to lightrag.operate")
                except ImportError:
                    pass
                    
                logger.info("Applied Robust Parser monkey patch (fixes 'found X/Y fields' errors)")
                
            except Exception as e:
                logger.warning(f"Failed to patch PROMPTS: {e}")
            
            # CRITICAL: Must call initialize_storages() before any operations
            # This initializes the _storage_lock and other async resources
            await self._rag.initialize_storages()
            
            # Post-init concurrency configuration
            # Setting these attributes directly since __init__ rejected them
            self._rag.embedding_func_max_async = 3
            self._rag.map_func_max_async = 3
            self._rag.reduce_func_max_async = 3
            self._rag.llm_model_func_max_async = 3
            print("Configured single-worker concurrency for Llama 3.1")
            logger.debug("RAG storages initialized")
            
            # Initialize pipeline status explicitly
            # (Required for newer LightRAG versions with PGKVStorage)
            try:
                if initialize_pipeline_status:
                    await initialize_pipeline_status()
                    logger.debug("Pipeline status initialized via shared_storage")
                elif hasattr(self._rag, "initialize_pipeline_status"):
                    await self._rag.initialize_pipeline_status()
                    logger.debug("Pipeline status initialized via RAG instance")
                else:
                    logger.warning("No pipeline status initialization method found - may cause KeyError")
            except Exception as e:
                logger.warning(f"Pipeline status initialization failed (may be OK): {e}")
                # Continue anyway - some versions may not need this
            
            self._initialized = True
            
            logger.info("✅ LightRAG initialized with PostgreSQL + Neo4j storage")
            return self._rag
            
        except Exception as e:
            logger.error(f"Failed to initialize LightRAG: {e}")
            raise
    
    @property
    def rag(self) -> LightRAG:
        """Get the LightRAG instance (must be initialized first)."""
        if not self._initialized or self._rag is None:
            raise RuntimeError("RAG not initialized. Call initialize() first.")
        return self._rag
    
    async def close(self):
        """Cleanup resources."""
        if self._rag is not None:
            # Close any open connections
            self._initialized = False
            self._rag = None
            logger.info("LightRAG resources cleaned up")


# Global RAG manager instance
_rag_manager: Optional[RAGManager] = None


def get_rag_manager() -> RAGManager:
    """Get or create global RAG manager."""
    global _rag_manager
    if _rag_manager is None:
        _rag_manager = RAGManager()
    return _rag_manager


async def get_rag() -> LightRAG:
    """Get initialized RAG instance."""
    manager = get_rag_manager()
    return await manager.initialize()


# Query parameter presets for different use cases
QUERY_PRESETS = {
    "naive": QueryParam(mode="naive"),
    "local": QueryParam(mode="local"),
    "global": QueryParam(mode="global"),
    "hybrid": QueryParam(mode="hybrid"),
    "mix": QueryParam(mode="mix"),
}


def get_query_param(mode: str = "mix") -> QueryParam:
    """Get QueryParam for specified mode."""
    return QUERY_PRESETS.get(mode, QUERY_PRESETS["mix"])
