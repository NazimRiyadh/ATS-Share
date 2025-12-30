"""
Configuration management endpoints.
Allows dynamic updates to system configuration at runtime.
"""

from pydantic import BaseModel, HttpUrl
from fastapi import APIRouter, HTTPException

from src.logging_config import get_logger
from src.llm_adapter import get_ollama_adapter

logger = get_logger(__name__)
router = APIRouter(prefix="/config", tags=["Configuration"])


class LLMUrlRequest(BaseModel):
    url: str


@router.post("/llm-url")
async def update_llm_url(request: LLMUrlRequest):
    """
    Update the Ollama LLM base URL dynamically.
    Useful for connecting to transient Colab/ngrok tunnels.
    """
    try:
        adapter = get_ollama_adapter()
        await adapter.set_base_url(request.url)
        
        # Verify connectivity
        is_healthy = await adapter.check_health()
        status = "connected" if is_healthy else "updated_but_unreachable"
        
        return {
            "message": f"LLM URL updated to {request.url}",
            "status": status,
            "url": request.url
        }
    except Exception as e:
        logger.error(f"Failed to update LLM URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))
