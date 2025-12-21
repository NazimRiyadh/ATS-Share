"""
BM25 Keyword Search Module for Hybrid Retrieval.
Uses rank-bm25 library for production-tested BM25 implementation.
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from src.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BM25SearchResult:
    """Result from BM25 search."""
    content: str
    score: float
    index: int


class BM25Index:
    """
    BM25 index for keyword-based resume search.
    Complements vector search for exact term matching.
    """
    
    def __init__(self):
        self._index: Optional[BM25Okapi] = None
        self._documents: List[str] = []
        self._tokenized_docs: List[List[str]] = []
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text with skill-aware preprocessing.
        Preserves important technical terms and handles common variations.
        """
        # Lowercase
        text = text.lower()
        
        # Normalize common skill variations
        skill_normalizations = {
            r'\breact\.?js\b': 'reactjs',
            r'\bnode\.?js\b': 'nodejs',
            r'\bvue\.?js\b': 'vuejs',
            r'\btype\s*script\b': 'typescript',
            r'\bjava\s*script\b': 'javascript',
            r'\bc\+\+\b': 'cplusplus',
            r'\bc#\b': 'csharp',
            r'\b\.net\b': 'dotnet',
            r'\baws\b': 'aws',
            r'\bgcp\b': 'gcp',
            r'\bazure\b': 'azure',
        }
        
        for pattern, replacement in skill_normalizations.items():
            text = re.sub(pattern, replacement, text)
        
        # Split into tokens (alphanumeric + some special chars)
        tokens = re.findall(r'\b[a-z0-9+#]+\b', text)
        
        # Remove very short tokens and common stopwords
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can'}
        tokens = [t for t in tokens if len(t) > 1 and t not in stopwords]
        
        return tokens
    
    def build_index(self, documents: List[str]) -> None:
        """
        Build BM25 index from documents.
        
        Args:
            documents: List of document texts (resume chunks)
        """
        self._documents = documents
        self._tokenized_docs = [self._tokenize(doc) for doc in documents]
        self._index = BM25Okapi(self._tokenized_docs)
        logger.info(f"Built BM25 index with {len(documents)} documents")
    
    def search(
        self,
        query: str,
        top_k: int = 20
    ) -> List[BM25SearchResult]:
        """
        Search documents using BM25.
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of BM25SearchResult sorted by score descending
        """
        if self._index is None or not self._documents:
            logger.warning("BM25 index not built, returning empty results")
            return []
        
        # Tokenize query
        query_tokens = self._tokenize(query)
        
        if not query_tokens:
            logger.warning("Query tokenized to empty, returning empty results")
            return []
        
        # Get BM25 scores
        scores = self._index.get_scores(query_tokens)
        
        # Create results with indices
        results = []
        for i, score in enumerate(scores):
            if score > 0:  # Only include non-zero scores
                results.append(BM25SearchResult(
                    content=self._documents[i],
                    score=float(score),
                    index=i
                ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Limit to top_k
        results = results[:top_k]
        
        logger.debug(f"BM25 search: query='{query[:50]}...', results={len(results)}")
        return results
    
    def get_document_count(self) -> int:
        """Return number of indexed documents."""
        return len(self._documents)


# Global index instance (singleton)
_bm25_index: Optional[BM25Index] = None


def get_bm25_index() -> BM25Index:
    """Get or create global BM25 index."""
    global _bm25_index
    if _bm25_index is None:
        _bm25_index = BM25Index()
    return _bm25_index


async def hybrid_search(
    query: str,
    documents: List[str],
    vector_scores: List[float],
    top_k: int = 20,
    bm25_weight: float = 0.3,
    vector_weight: float = 0.5,
    graph_weight: float = 0.2,
    graph_bonus: Optional[List[float]] = None
) -> List[Dict]:
    """
    Perform hybrid search combining BM25 + Vector + Graph scores.
    
    Args:
        query: Search query
        documents: List of document texts
        vector_scores: Vector similarity scores (same order as documents)
        top_k: Number of top results
        bm25_weight: Weight for BM25 scores (default 0.3)
        vector_weight: Weight for vector scores (default 0.5)
        graph_weight: Weight for graph bonus (default 0.2)
        graph_bonus: Optional graph-based bonus scores
        
    Returns:
        List of dicts with 'content', 'score', 'index', 'score_breakdown'
    """
    # Build BM25 index
    bm25_index = get_bm25_index()
    bm25_index.build_index(documents)
    
    # Get BM25 results
    bm25_results = bm25_index.search(query, top_k=len(documents))
    
    # Create score map from BM25
    bm25_score_map = {r.index: r.score for r in bm25_results}
    
    # Normalize BM25 scores to 0-1 range
    if bm25_score_map:
        max_bm25 = max(bm25_score_map.values())
        if max_bm25 > 0:
            bm25_score_map = {k: v / max_bm25 for k, v in bm25_score_map.items()}
    
    # Normalize vector scores to 0-1 range
    max_vector = max(vector_scores) if vector_scores else 1.0
    min_vector = min(vector_scores) if vector_scores else 0.0
    range_vector = max_vector - min_vector if max_vector != min_vector else 1.0
    normalized_vector = [(s - min_vector) / range_vector for s in vector_scores]
    
    # Default graph bonus if not provided
    if graph_bonus is None:
        graph_bonus = [0.0] * len(documents)
    
    # Calculate hybrid scores
    results = []
    for i, doc in enumerate(documents):
        bm25_score = bm25_score_map.get(i, 0.0)
        vec_score = normalized_vector[i] if i < len(normalized_vector) else 0.0
        g_bonus = graph_bonus[i] if i < len(graph_bonus) else 0.0
        
        hybrid_score = (
            bm25_weight * bm25_score +
            vector_weight * vec_score +
            graph_weight * g_bonus
        )
        
        results.append({
            'content': doc,
            'score': hybrid_score,
            'index': i,
            'score_breakdown': {
                'bm25': round(bm25_score, 3),
                'vector': round(vec_score, 3),
                'graph': round(g_bonus, 3)
            }
        })
    
    # Sort by hybrid score descending
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Limit to top_k
    results = results[:top_k]
    
    logger.info(f"Hybrid search: {len(results)} results (weights: BM25={bm25_weight}, Vec={vector_weight}, Graph={graph_weight})")
    
    return results
