"""
Embedding function using local Hugging Face model (sentence-transformers).
Provides LightRAG-compatible embedding function.
"""

import logging
from typing import List, Optional, Union
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from .config import settings

from src.logging_config import get_logger

logger = get_logger(__name__)


class LocalEmbeddingModel:
    """Embedding model wrapper for SentenceTransformer."""
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        embedding_dim: int = 1024,
        device: str = None
    ):
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        logger.info(f"Loading embedding model '{model_name}' on device: {self.device}")
        self._model = SentenceTransformer(model_name, device=self.device)

    def encode(
        self,
        texts: Union[str, List[str]],
        batch_size: int = 32,
        show_progress_bar: bool = False,
        normalize_embeddings: bool = True
    ) -> np.ndarray:
        """Generate embeddings via local model."""
        if isinstance(texts, str):
            texts = [texts]
            
        try:
            embeddings = self._model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress_bar,
                normalize_embeddings=normalize_embeddings,
                convert_to_numpy=True
            )
            return embeddings
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            raise

    async def aencode(self, texts: Union[str, List[str]], **kwargs) -> np.ndarray:
        """Async wrapper for compatibility."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.encode(texts, **kwargs))


# Global model instance
_embedding_model: Optional[LocalEmbeddingModel] = None


def get_embedding_model() -> LocalEmbeddingModel:
    """Get or create global embedding model."""
    global _embedding_model
    if _embedding_model is None:
        model_name = settings.embedding_model or "BAAI/bge-m3"
        logger.info(f"Initializing Local Embedding Model ({model_name})")
        _embedding_model = LocalEmbeddingModel(model_name=model_name) 
    return _embedding_model


async def embedding_func(texts: Union[str, List[str]]) -> np.ndarray:
    """LightRAG-compatible embedding function."""
    model = get_embedding_model()
    return await model.aencode(texts)


def embedding_func_sync(texts: Union[str, List[str]]) -> np.ndarray:
    """Synchronous version of embedding_func."""
    model = get_embedding_model()
    return model.encode(texts)
