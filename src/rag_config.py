"""
LightRAG configuration and initialization.
Sets up LightRAG with PostgreSQL vector storage and Neo4j graph storage.
"""

import os
import logging
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
            
            # Initialize LightRAG with PostgreSQL (vectors) and Neo4j (graph)
            # Monkey Patch FIRST: Inject custom prompt and delimiters for Llama 3.1
            # We modify the global PROMPTS dictionary which extract_entities reads
            try:
                from lightrag.prompt import PROMPTS
                
                # Override the entity extraction prompt with ATS-specific version
                # Correct key for LightRAG 1.4.9.8 is "entity_extraction_system_prompt"
                PROMPTS["entity_extraction_system_prompt"] = """You are an expert at extracting entities and relationships from text.
Your goal is to extract structured information about entities and their relationships.
The output format is STRICT. Follow the examples and constraints precisely.

    -Entity Types-
    PERSON       : Candidate full name
    SKILL        : Technical or professional skill
    ROLE         : Job title or role
    COMPANY      : Organization/company name
    CERTIFICATION: Formal certification or license
    LOCATION     : City, state, or country
    EXPERIENCE   : Years of experience (e.g., "5 years", "3+ years Python")

    -Relationship Types-
    HAS_SKILL, HAS_ROLE, WORKED_AT, HAS_CERTIFICATION, LOCATED_IN, HAS_EXPERIENCE

    -Output Format (STRICT)-
    ONE TUPLE PER LINE.
    Entity tuple:     ("entity"###<canonical_name>###<ENTITY_TYPE>###<brief description>)
    Relationship tuple: ("relationship"###<source>###<target>###<RELATIONSHIP_TYPE>###<evidence phrase>)
    
    -Examples-
    ("entity"###John Doe###PERSON###Candidate name)
    ("entity"###Python###SKILL###Programming language)
    ("entity"###5 years###EXPERIENCE###Total professional experience)
    ("entity"###3 years Python###EXPERIENCE###Skill-specific experience)
    ("relationship"###John Doe###Python###HAS_SKILL###Listed in skills section)
    ("relationship"###John Doe###Google###WORKED_AT###Employment history)
    ("relationship"###John Doe###5 years###HAS_EXPERIENCE###Summary section)
    
    -Constraints-
    1. Do NOT add quotes around values unless part of the name
    2. Do NOT add markdown, code blocks, or extra text
    3. Output specific tuples only
    4. Every relationship MUST reference entities that are explicitly extracted
    5. PERSON must be the source for all resume-derived facts
    6. If a tuple is incomplete or cannot be extracted, output NOTHING for that tuple
    7. Do NOT split tuples across lines or chunks; ensure each tuple is complete
    8. Use only "###" as the delimiter.
    9. **CRITICAL**: Do NOT label relationships as "entity". 
    10. Output NOTHING if no valid entities or relationships exist in the text
    11. **CRITICAL**: Do NOT use "UNKNOWN", "OTHER", or generic types. If the type is uncertain, SKIP the entity.
    12. **CRITICAL**: Do NOT output "None" or empty fields.
    13. **CRITICAL**: Extract EXPERIENCE entities for any mentioned years of experience.
    
    -Text-
    {input_text}
    
    -Output-
"""
                PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "###"
                PROMPTS["DEFAULT_RECORD_DELIMITER"] = "\n"
                PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "\n\n"
                
                # CRITICAL: Override examples to use pipe delimiter with PERSON-centric relationships
                PROMPTS["entity_extraction_examples"] = [
                    """("entity"###John Doe###PERSON###Candidate name)
("entity"###Python###SKILL###Programming language)
("entity"###Senior Data Analyst###ROLE###Job title)
("entity"###Google###COMPANY###Technology company)
("entity"###San Francisco###LOCATION###City in California)
("entity"###AWS Certified###CERTIFICATION###Cloud certification)
("relationship"###John Doe###Python###HAS_SKILL###Listed in skills section)
("relationship"###John Doe###Senior Data Analyst###HAS_ROLE###Current position)
("relationship"###John Doe###Google###WORKED_AT###Employment history)
("relationship"###John Doe###San Francisco###LOCATED_IN###Resume header)
("relationship"###John Doe###AWS Certified###HAS_CERTIFICATION###Certifications section)"""
                ]
                
                print("DEBUG: Applied PROMPTS monkey patch for Llama 3.1 format")
            except Exception as e:
                print(f"DEBUG: Failed to patch PROMPTS: {e}")

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
                
                # print(f"DEBUG: Robust Parser Called with {len(content)} chars")
                results = [content]
                for marker in markers:
                    new_results = []
                    for r in results:
                        new_results.extend(r.split(marker))
                    results = new_results
                
                results = [r.strip() for r in results if r.strip()]
                
                if not results:
                    return []
                
                # GUARD CLAUSE: If splitting by newline (lines detection), return raw results
                # We only want to apply smart logic when splitting fields (###)
                if any('\n' in m for m in markers):
                     return results

                # Normalize first token to check type (safely ignore quotes/parens)
                first_token = results[0].lower().strip('("')

                # SAFER CLEANING: Only modify if we likely have a tuple (split succeeded)
                if len(results) >= 3:
                     # Remove leading/trailing parens/quotes from first element (Type)
                     # use strip() because type token is quoted like "entity"
                     results[0] = results[0].strip('("')
                     # Remove trailing parens/quotes from last element
                     results[-1] = results[-1].rstrip(')"')
                     
                     # Ensure canonical type name is clean
                     if "entity" in first_token:
                         results[0] = "entity"
                     elif "relationship" in first_token:
                         results[0] = "relationship"
                
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
                # CRITICAL: Only apply if we actually split something (len > 1)
                # Otherwise we might corrupt a full line that failed to split
                # ---------------------------------------------------------
                if len(results) > 1:
                    if "entity" in first_token:
                        # Expected: ("entity", Name, Type, Description) -> 4 fields
                        if len(results) > 4:
                            results = results[:4]
                        elif len(results) < 4:
                            results.extend(["Description not provided"] * (4 - len(results)))
                            
                    elif "relationship" in first_token:
                        # Expected: ("relationship", Src, Tgt, RelType, Desc) -> 5 fields
                        if len(results) > 5:
                            results = results[:5]
                        elif len(results) < 5:
                            results.extend(["Evidence not provided"] * (5 - len(results)))

                # =========================================================
                # ENTITY RESOLUTION INTEGRATION
                # =========================================================
                try:
                    # Lazy import to avoid circular dependencies if any
                    from src.entity_resolver import get_entity_resolver
                    resolver = get_entity_resolver()
                    
                    if "entity" in first_token and len(results) >= 3:
                        # Format: ("entity", Name, Type, Description)
                        entity_name = results[1]
                        entity_type = results[2]
                        
                        resolved = resolver.resolve_entity(entity_name, entity_type)
                        results[1] = resolved.canonical
                        
                        # Optional: Update type if resolver corrected it (e.g. inferred from name)
                        results[2] = resolved.entity_type.value
                        
                    elif "relationship" in first_token and len(results) >= 4:
                        # Format: ("relationship", Src, Tgt, RelType, Desc)
                        rel_type = results[3]
                        is_valid, canonical_type = resolver.validate_relationship_type(rel_type)
                        results[3] = canonical_type
                        
                        # Also resolve source/target names if possible? 
                        # Ideally yes, but we don't know their types easily here.
                        # Infer Target Type from RelType
                        target_type_map = {
                            "HAS_SKILL": "SKILL",
                            "REQUIRES_SKILL": "SKILL",
                            "WORKED_AT": "COMPANY",
                            "HAS_ROLE": "ROLE",
                            "LOCATED_IN": "LOCATION",
                            "HAS_CERTIFICATION": "CERTIFICATION",
                            "HAS_EDUCATION": "EDUCATION"
                        }
                        
                        target_type = target_type_map.get(str(canonical_type).upper(), "UNKNOWN")
                        
                        # Resolve Source (Assume PERSON usually, or fallback)
                        # For generated CVs, source is usually the candidate name (PERSON)
                        source_resolved = resolver.resolve_entity(results[1], "PERSON")
                        results[1] = source_resolved.canonical
                        
                        # Resolve Target
                        if target_type != "UNKNOWN":
                             target_resolved = resolver.resolve_entity(results[2], target_type)
                             results[2] = target_resolved.canonical
                        else:
                             # Fallback cleaning
                             results[2] = resolver._clean_entity_name(results[2])
                            
                except Exception as e:
                    # Fail safe - don't stop ingestion if resolution crashes
                    pass

                if len(results) >= 2:
                    pass
                print(f"DEBUG PARSER: {results} MARKERS: {markers}")
                return results

            # Overwrite the utility function directly in utils
            print("DEBUG: Attempting to patch lightrag.utils")
            lightrag.utils.split_string_by_multi_markers = robust_split_string_by_multi_markers
            print("DEBUG: Patched lightrag.utils")
            
            # ==========================================================
            # MONKEY PATCH: Override _process_extraction_result
            # Bypass "Fix LLM output format error" logic in operate.py
            # ==========================================================
            async def _custom_process_extraction_result(
                result: str,
                chunk_key: str,
                timestamp: int,
                file_path: str = "unknown_source",
                tuple_delimiter: str = "<|#|>",
                completion_delimiter: str = "<|COMPLETE|>",
            ) -> tuple[dict, dict]:
                """
                Simplified processor for Llama 3.1 tuple output.
                Splits purely by newline and doesn't try to auto-fix missing 'entity' prefixes.
                """
                from collections import defaultdict
                import lightrag.operate
                from lightrag.operate import (
                    split_string_by_multi_markers, 
                    fix_tuple_delimiter_corruption,
                    _handle_single_entity_extraction,
                    _handle_single_relationship_extraction,
                    _truncate_entity_identifier,
                    DEFAULT_ENTITY_NAME_MAX_LENGTH,
                    logger
                )
                
                maybe_nodes = defaultdict(list)
                maybe_edges = defaultdict(list)
                
                # print(f"DEBUG: Processing chunk {chunk_key} ({len(result)} chars)")

                # Basic splitting
                if completion_delimiter in result:
                     result = result.split(completion_delimiter)[0]
                
                # Split by newline (default record delimiter)
                records = split_string_by_multi_markers(result, ["\n"])
                
                # DIRECTLY process records without the "fix" logic that corrupts tuples
                fixed_records = records

                for record in fixed_records:
                    record = record.strip()
                    if not record:
                        continue
                    
                    # Fix delimiter corruption (###) if needed
                    delimiter_core = tuple_delimiter.replace("<|","").replace("|>","") # e.g. "###"
                    record = fix_tuple_delimiter_corruption(record, delimiter_core, tuple_delimiter)
                    
                    # Split into attributes using our ROBUST parser
                    # This calls our monkey-patched split_string_by_multi_markers
                    record_attributes = split_string_by_multi_markers(record, [tuple_delimiter])
                    
                    # Try to parse as entity
                    entity_data = await _handle_single_entity_extraction(
                        record_attributes, chunk_key, timestamp, file_path
                    )
                    if entity_data is not None:
                        truncated_name = _truncate_entity_identifier(
                            entity_data["entity_name"],
                            DEFAULT_ENTITY_NAME_MAX_LENGTH,
                            chunk_key,
                            "Entity name",
                        )
                        entity_data["entity_name"] = truncated_name
                        maybe_nodes[truncated_name].append(entity_data)
                        continue

                    # Try to parse as relationship
                    relationship_data = await _handle_single_relationship_extraction(
                        record_attributes, chunk_key, timestamp, file_path
                    )
                    if relationship_data is not None:
                        truncated_source = _truncate_entity_identifier(
                            relationship_data["src_id"],
                            DEFAULT_ENTITY_NAME_MAX_LENGTH,
                            chunk_key,
                            "Relation entity",
                        )
                        truncated_target = _truncate_entity_identifier(
                            relationship_data["tgt_id"],
                            DEFAULT_ENTITY_NAME_MAX_LENGTH,
                            chunk_key,
                            "Relation entity",
                        )
                        relationship_data["src_id"] = truncated_source
                        relationship_data["tgt_id"] = truncated_target
                        relationship_data["src_id"] = truncated_source
                        relationship_data["tgt_id"] = truncated_target
                        print(f"DEBUG: Adding relation to maybe_edges: {truncated_source} -> {truncated_target} ({relationship_data.get('relation_name')})")
                        maybe_edges[(truncated_source, truncated_target)].append(relationship_data)

                return dict(maybe_nodes), dict(maybe_edges)

            # Apply the patch to operate module
            try:
                import lightrag.operate
                lightrag.operate._process_extraction_result = _custom_process_extraction_result
                logger.info("Applied Custom Processor monkey patch to lightrag.operate")
            except Exception as e:
                logger.warning(f"Failed to patch _process_extraction_result: {e}")

            # Also overwrite in operate module if it was imported directly
            try:
                import lightrag.operate
                lightrag.operate.split_string_by_multi_markers = robust_split_string_by_multi_markers
                logger.info("Applied Robust Parser monkey patch to lightrag.operate")
            except ImportError:
                pass
                
            logger.info("Applied Robust Parser monkey patch (fixes 'found X/Y fields' errors)")
            
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
            
            logger.info("LightRAG initialized with PostgreSQL + Neo4j storage")
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
