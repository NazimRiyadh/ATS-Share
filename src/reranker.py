"""
Cross-encoder reranking model for candidate scoring.
Uses ms-marco-MiniLM-L-6-v2 for efficient reranking.
"""

import logging
from typing import List, Tuple, Optional
import numpy as np

from sentence_transformers import CrossEncoder

from .config import settings

from src.logging_config import get_logger

logger = get_logger(__name__)


class RerankerModel:
    """Cross-encoder reranking model."""
    
    def __init__(self, model_name: str = None, device: str = None):
        self.model_name = model_name or settings.rerank_model
        self.device = device
        self._model: Optional[CrossEncoder] = None
    
    def _ensure_model_loaded(self):
        """Lazy load the model."""
        if self._model is None:
            logger.info(f"Loading reranker model: {self.model_name}")
            self._model = CrossEncoder(
                self.model_name,
                device=self.device
            )
            logger.info(f"✅ Reranker model loaded")
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
        return_scores: bool = True
    ) -> List[Tuple[int, float, str]]:
        """
        Rerank documents based on relevance to query.
        
        Args:
            query: The search query
            documents: List of document texts to rerank
            top_k: Number of top results to return (None = all)
            return_scores: Include scores in results
            
        Returns:
            List of (original_index, score, document) tuples, sorted by score descending
        """
        self._ensure_model_loaded()
        
        if not documents:
            return []
        
        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]
        
        # Get scores
        scores = self._model.predict(pairs)
        
        # Create indexed results
        results = [(i, float(scores[i]), documents[i]) for i in range(len(documents))]
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Apply top_k if specified
        if top_k is not None:
            results = results[:top_k]
        
        logger.debug(f"Reranked {len(documents)} documents, returning top {len(results)}")
        return results
    
    async def arerank(
        self,
        query: str,
        documents: List[str],
        **kwargs
    ) -> List[Tuple[int, float, str]]:
        """Async wrapper for rerank."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.rerank(query, documents, **kwargs)
        )


# Global model instance
_reranker_model: Optional[RerankerModel] = None


def get_reranker_model() -> RerankerModel:
    """Get or create global reranker model."""
    global _reranker_model
    if _reranker_model is None:
        _reranker_model = RerankerModel()
    return _reranker_model


async def rerank_func(
    query: str,
    documents: List[str],
    top_n: int = 10,
    **kwargs
) -> List[dict]:
    """
    LightRAG-compatible reranking function.
    
    Args:
        query: Search query
        documents: Documents to rerank
        top_n: Number of top results (LightRAG's parameter name)
        **kwargs: Accept any additional parameters from LightRAG
        
    Returns:
        List of dicts with 'content' and 'score' keys (LightRAG format)
    """
    model = get_reranker_model()
    results = await model.arerank(query, documents, top_k=top_n)
    
    # Convert tuples to dictionaries for LightRAG compatibility
    return [{"content": r[2], "relevance_score": r[1], "index": r[0]} for r in results]


def rerank_func_sync(
    query: str,
    documents: List[str],
    top_k: int = 10
) -> List[Tuple[int, float, str]]:
    """Synchronous version of rerank_func."""
    model = get_reranker_model()
    return model.rerank(query, documents, top_k=top_k)
