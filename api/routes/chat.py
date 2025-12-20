"""
Chat endpoint with dual-level retrieval.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException

from api.models import (
    JobChatRequest,
    DirectQueryRequest,
    ChatResponse
)
from src.rag_config import get_rag
from src.dual_retrieval import (
    DualLevelRetrieval,
    CandidateContext,
    chat_with_dual_retrieval
)
from api.routes.analyze import get_job_context

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/job", response_model=ChatResponse)
async def chat_about_job(request: JobChatRequest):
    """
    Chat about candidates for a specific job using dual-level retrieval.
    
    This endpoint:
    1. Retrieves stored job context (from /analyze_job)
    2. Performs dual-level retrieval (vector + graph)
    3. Returns LLM response with source attribution
    
    Modes:
    - naive: Pure vector search
    - local: Entity-specific retrieval
    - global: Relationship-based retrieval
    - hybrid: Local + Global combined
    - mix: Full dual-level (recommended)
    """
    start_time = datetime.now()
    
    # Get job context
    job_context = get_job_context(request.job_id)
    
    if not job_context:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {request.job_id}. Please run /analyze first."
        )
    
    try:
        # Get RAG instance
        rag = await get_rag()
        
        # Prepare candidate context from stored analysis
        candidates = []
        for c in job_context.get("candidates", []):
            candidates.append(CandidateContext(
                name=c.name if hasattr(c, 'name') else c.get('name', 'Unknown'),
                content=str(c.highlights) if hasattr(c, 'highlights') else str(c.get('highlights', [])),
                score=c.score if hasattr(c, 'score') else c.get('score', 0.0),
                metadata={}
            ))
        
        # Construct enhanced query with job context
        enhanced_query = f"""
Job Requirements: {job_context.get('query', '')}

User Question: {request.message}
"""
        
        # Perform dual-level retrieval
        result = await chat_with_dual_retrieval(
            rag=rag,
            query=enhanced_query,
            candidates=candidates,
            mode=request.mode
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ChatResponse(
            response=result["response"],
            mode_used=result["mode_used"],
            fallback_used=result.get("fallback_used", False),
            sources=result.get("sources", {}),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=ChatResponse)
async def direct_query(request: DirectQueryRequest):
    """
    Direct query without job context.
    
    Useful for general questions about the candidate pool.
    """
    start_time = datetime.now()
    
    try:
        rag = await get_rag()
        
        result = await chat_with_dual_retrieval(
            rag=rag,
            query=request.query,
            candidates=None,
            mode=request.mode
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ChatResponse(
            response=result["response"],
            mode_used=result["mode_used"],
            fallback_used=result.get("fallback_used", False),
            sources=result.get("sources", {}),
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modes")
async def get_available_modes():
    """
    Get available retrieval modes with descriptions.
    """
    return {
        "modes": {
            "naive": {
                "description": "Pure vector similarity search",
                "use_case": "Fast, general semantic search",
                "speed": "fastest"
            },
            "local": {
                "description": "Entity-specific retrieval",
                "use_case": "Questions about specific candidates or skills",
                "speed": "fast"
            },
            "global": {
                "description": "Relationship-based retrieval",
                "use_case": "Pattern analysis, technology landscape",
                "speed": "medium"
            },
            "hybrid": {
                "description": "Local + Global combined",
                "use_case": "Complex queries needing depth and breadth",
                "speed": "medium"
            },
            "mix": {
                "description": "Full dual-level retrieval (vector + graph)",
                "use_case": "Best overall results (recommended)",
                "speed": "slower"
            }
        },
        "default": "mix",
        "recommended": "mix"
    }
