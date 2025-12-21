"""
Custom dual-level retrieval combining vector search with knowledge graph queries.
Implements fallback mechanisms for robust retrieval.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from lightrag import LightRAG, QueryParam

from .config import settings
from .prompts import CHAT_RESPONSE_PROMPT

from src.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """Container for retrieval results with source attribution."""
    response: str
    mode_used: str
    sources: Dict[str, Any]
    fallback_used: bool = False


@dataclass
class CandidateContext:
    """Context for a shortlisted candidate."""
    name: str
    content: str
    score: float
    metadata: Dict[str, Any]


class DualLevelRetrieval:
    """
    Custom dual-level retrieval system combining:
    1. Vector search for semantic similarity
    2. Knowledge graph queries for entity/relationship context
    3. Automatic fallback on mode failures
    """
    
    # Fallback chain from most sophisticated to simplest
    FALLBACK_CHAIN = ["mix", "hybrid", "local", "naive"]
    
    def __init__(self, rag: LightRAG):
        self.rag = rag
    
    async def query_with_mode(
        self,
        query: str,
        mode: str = "mix"
    ) -> Tuple[Optional[str], str]:
        """
        Query using specified mode with error handling.
        
        Args:
            query: Search query
            mode: Retrieval mode
            
        Returns:
            Tuple of (response, mode_used)
        """
        try:
            response = await self.rag.aquery(
                query,
                param=QueryParam(mode=mode)
            )
            if response:
                logger.info(f"✅ Query succeeded with mode: {mode}")
                return response, mode
            else:
                logger.warning(f"Mode '{mode}' returned empty response")
                return None, mode
                
        except Exception as e:
            logger.warning(f"Mode '{mode}' failed: {e}")
            return None, mode
    
    async def query_with_fallback(
        self,
        query: str,
        preferred_mode: str = "mix"
    ) -> RetrievalResult:
        """
        Query with automatic fallback through mode chain.
        
        Args:
            query: Search query
            preferred_mode: Initial mode to try
            
        Returns:
            RetrievalResult with response and metadata
        """
        # Build fallback chain starting with preferred mode
        if preferred_mode in self.FALLBACK_CHAIN:
            start_idx = self.FALLBACK_CHAIN.index(preferred_mode)
            fallback_chain = self.FALLBACK_CHAIN[start_idx:]
        else:
            fallback_chain = [preferred_mode] + self.FALLBACK_CHAIN
        
        sources = {"attempted_modes": [], "errors": []}
        
        for mode in fallback_chain:
            sources["attempted_modes"].append(mode)
            response, used_mode = await self.query_with_mode(query, mode)
            
            if response:
                return RetrievalResult(
                    response=response,
                    mode_used=used_mode,
                    sources=sources,
                    fallback_used=(used_mode != preferred_mode)
                )
        
        # All modes failed - return error
        logger.error("All retrieval modes failed")
        return RetrievalResult(
            response="Unable to retrieve relevant information. Please try rephrasing your query.",
            mode_used="none",
            sources=sources,
            fallback_used=True
        )
    
    async def dual_level_query(
        self,
        query: str,
        candidates: Optional[List[CandidateContext]] = None,
        mode: str = "mix"
    ) -> RetrievalResult:
        """
        Perform dual-level retrieval combining multiple sources.
        
        This method:
        1. Queries LightRAG (which internally uses vector + graph)
        2. Optionally injects candidate context
        3. Aggregates results with source attribution
        
        Args:
            query: User query
            candidates: Optional pre-shortlisted candidates
            mode: Preferred retrieval mode
            
        Returns:
            RetrievalResult with aggregated context
        """
        sources = {
            "vector_context": "",
            "graph_context": "",
            "candidate_context": "",
            "context_lengths": {}
        }
        
        # Step 1: Query LightRAG with fallback
        rag_result = await self.query_with_fallback(query, mode)
        sources["vector_context"] = rag_result.response
        sources["context_lengths"]["rag"] = len(rag_result.response)
        
        # Step 2: Add candidate context if provided
        if candidates:
            candidate_texts = []
            for c in candidates:
                candidate_texts.append(
                    f"**{c.name}** (Score: {c.score:.2f}):\n{c.content[:500]}..."
                )
            sources["candidate_context"] = "\n\n".join(candidate_texts)
            sources["context_lengths"]["candidates"] = len(sources["candidate_context"])
        
        # Step 3: Aggregate context
        total_context = self._aggregate_context(sources)
        sources["context_lengths"]["total"] = len(total_context)
        
        # Log retrieval stats
        self._log_retrieval_stats(sources)
        
        return RetrievalResult(
            response=total_context,
            mode_used=rag_result.mode_used,
            sources=sources,
            fallback_used=rag_result.fallback_used
        )
    
    def _aggregate_context(self, sources: Dict[str, Any]) -> str:
        """Combine multiple context sources into unified context."""
        parts = []
        
        if sources.get("vector_context"):
            parts.append("## Retrieved Information\n" + sources["vector_context"])
        
        if sources.get("candidate_context"):
            parts.append("## Shortlisted Candidates\n" + sources["candidate_context"])
        
        return "\n\n".join(parts)
    
    def _log_retrieval_stats(self, sources: Dict[str, Any]) -> None:
        """Log retrieval statistics."""
        lengths = sources.get("context_lengths", {})
        logger.info(
            f"🔍 Dual-Level Retrieval:\n"
            f"  📊 RAG: {lengths.get('rag', 0)} chars\n"
            f"  📋 Candidates: {lengths.get('candidates', 0)} chars\n"
            f"  ✅ Total: {lengths.get('total', 0)} chars"
        )


# Grounding wrapper prompt to prevent LLM hallucination
GROUNDING_PROMPT = """You are a helpful ATS assistant helping a recruiter find the right candidates.

CONTEXT - Candidate Information:
{context}

USER QUESTION:
{query}

INSTRUCTIONS:
- Answer the question directly and naturally, like a helpful colleague
- Use ONLY the candidate information provided above
- If you mention a candidate, include their relevant skills and experience
- If no candidates match, say "I don't see any candidates matching that requirement"
- Be concise and specific - focus on what the recruiter asked
- DO NOT use phrases like "based on the document chunks" or "according to the data"
- DO NOT talk about your limitations or how you process information

YOUR ANSWER:
"""


async def chat_with_dual_retrieval(
    rag: LightRAG,
    query: str,
    candidates: Optional[List[CandidateContext]] = None,
    mode: str = "mix"
) -> Dict[str, Any]:
    """
    High-level function for chat with dual-level retrieval.
    Uses grounded approach: retrieve raw context first, then LLM with strict grounding.
    
    PRODUCTION HARDENED:
    - AUDIT FIX 3: Validates LLM response references actual context
    
    Args:
        rag: LightRAG instance
        query: User question
        candidates: Optional shortlisted candidates
        mode: Retrieval mode
        
    Returns:
        Dict with response and metadata
    """
    from .llm_adapter import ollama_llm_func
    
    retrieval = DualLevelRetrieval(rag)
    
    # MODIFIED: If candidates provided (from /analyze), use ONLY them - skip RAG query
    if candidates:
        logger.info(f"🎯 Using ONLY pre-analyzed candidates (skipping full graph query)")
        
        # Build context from candidates only
        candidate_section = "## ANALYZED CANDIDATES:\n\n"
        for c in candidates:
            candidate_section += f"**{c.name}** (Match Score: {c.score:.1%})\n"
            candidate_section += f"{c.content}\n\n"
        
        # DEBUG: Log what we're using
        logger.info(f"📋 Using {len(candidates)} pre-analyzed candidates")
        for i, c in enumerate(candidates, 1):
            logger.info(f"   {i}. {c.name} (Score: {c.score:.2f})")
        
        grounded_prompt = GROUNDING_PROMPT.format(
            context=candidate_section,
            query=query
        )
        
        try:
            grounded_response = await ollama_llm_func(grounded_prompt)
            
            # Validate response against candidate context
            validation_result = validate_grounded_response(grounded_response, candidate_section)
            
            if validation_result["valid"]:
                logger.info("✅ Generated validated response from pre-analyzed candidates")
                return {
                    "response": grounded_response,
                    "mode_used": "candidates-only (grounded)",
                    "fallback_used": False,
                    "sources": {"candidates": len(candidates), "total_context": len(candidate_section)}
                }
            else:
                logger.warning(f"⚠️  Response validation failed: {validation_result['reason']}")
                # Still return the response but mark as unvalidated
                return {
                    "response": grounded_response,
                    "mode_used": "candidates-only (unvalidated)",
                    "fallback_used": False,
                    "sources": {"candidates": len(candidates), "total_context": len(candidate_section)}
                }
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {
                "response": f"Error generating response from candidates: {str(e)}",
                "mode_used": "error",
                "fallback_used": True,
                "sources": {"candidates": len(candidates)}
            }
    
    # ORIGINAL FLOW: No candidates provided - do full RAG retrieval
    # Step 1: Get raw context using only_need_context parameter
    # This bypasses LightRAG's internal LLM call and returns raw chunks
    try:
        raw_context = await rag.aquery(
            query,
            param=QueryParam(mode=mode, only_need_context=True)
        )
        logger.info(f"📄 Retrieved {len(raw_context) if raw_context else 0} chars of raw context")
    except Exception as e:
        logger.warning(f"Raw context retrieval failed: {e}, falling back to standard mode")
        raw_context = None
    
    # Step 2: If raw context retrieval worked, use grounded LLM call
    if raw_context:
        grounded_prompt = GROUNDING_PROMPT.format(
            context=raw_context,
            query=query
        )
        
        try:
            grounded_response = await ollama_llm_func(grounded_prompt)
            
            # Validate LLM response references actual context
            validation_result = validate_grounded_response(grounded_response, raw_context)
            
            if validation_result["valid"]:
                logger.info("✅ Generated validated grounded response")
                return {
                    "response": grounded_response,
                    "mode_used": f"{mode} (grounded, validated)",
                    "fallback_used": False,
                    "sources": {"rag": len(raw_context), "total": len(raw_context)}
                }
            else:
                logger.warning(f"⚠️  LLM response failed validation: {validation_result['reason']}")
                # Return a safe response instead of potentially hallucinated content
                return {
                    "response": f"Based on the resume data, I found relevant candidates but cannot provide specific details. {validation_result['reason']}",
                    "mode_used": f"{mode} (grounded, validation failed)",
                    "fallback_used": True,
                    "sources": {"rag": len(raw_context), "total": len(raw_context)}
                }
                
        except Exception as e:
            logger.warning(f"Grounded LLM call failed: {e}")
    
    # Step 3: Fallback to standard dual-level retrieval if grounding fails
    result = await retrieval.dual_level_query(query, candidates, mode)
    
    return {
        "response": result.response,
        "mode_used": result.mode_used,
        "fallback_used": result.fallback_used,
        "sources": result.sources.get("context_lengths", {})
    }


def validate_grounded_response(response: str, context: str) -> Dict[str, Any]:
    """
    AUDIT FIX 3: Validate that LLM response is grounded in actual context.
    
    Checks:
    1. Response is not empty or just filler
    2. Response contains specific terms from context
    3. Response doesn't make claims not in context
    
    Returns:
        Dict with 'valid' boolean and 'reason' string
    """
    import re
    
    # Check 1: Response is not empty or too short
    if not response or len(response.strip()) < 10:
        return {"valid": False, "reason": "Response too short to be meaningful"}
    
    # Check 2: Response doesn't end with incomplete sentence
    response_stripped = response.strip()
    if response_stripped.endswith(':') or response_stripped.endswith('following'):
        return {"valid": False, "reason": "Response appears truncated"}
    
    # Check 3: Extract potential names from context and check if any appear in response
    # Look for capitalized names (2-3 words) to avoid common words
    name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b'
    
    # helper to normalize names for comparison
    def normalize_names(text):
        matches = re.findall(name_pattern, text)
        return {m.lower() for m in matches}

    context_names = normalize_names(context)
    response_names = normalize_names(response)
    
    # If context has names, response should reference at least one valid one
    if context_names and response_names:
        # Check intersection (exact match ignoring case)
        exact_matches = context_names & response_names
        
        # Check partial match (e.g. "Tammy" in "Tammy McKenzie")
        partial_matches = False
        if not exact_matches:
            for r_name in response_names:
                for c_name in context_names:
                    # If response name parts are subset of context name parts
                    r_parts = set(r_name.split())
                    c_parts = set(c_name.split())
                    if r_parts & c_parts: # Overlap found
                        partial_matches = True
                        break
                if partial_matches: break

        if not exact_matches and not partial_matches:
            # Check if it's a "no candidate found" type response
            if "no candidate" not in response.lower() and "not find" not in response.lower() and "cannot provide" not in response.lower():
                 return {"valid": False, "reason": "Response contains names not found in resume data"}
    
    # Check 4: Response shouldn't contain self-referential statements
    hallucination_markers = [
        "i have been trained",
        "as an ai",
        "i don't have access",
        "i cannot access",
        "my knowledge",
        "my training"
    ]
    response_lower = response.lower()
    for marker in hallucination_markers:
        if marker in response_lower:
            return {"valid": False, "reason": "Response contains self-referential AI statements"}
    
    return {"valid": True, "reason": ""}



async def grounded_query(rag: LightRAG, query: str) -> str:
    """
    Simple grounded query - prevents hallucination by enforcing context usage.
    
    This is a convenience wrapper around chat_with_dual_retrieval for simple queries.
    
    Args:
        rag: LightRAG instance
        query: User question
        
    Returns:
        Grounded response string
    """
    result = await chat_with_dual_retrieval(rag, query)
    return result["response"]
