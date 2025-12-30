"""
Ollama LLM adapter for LightRAG integration.
Provides async LLM function compatible with LightRAG's llm_model_func parameter.
"""

import asyncio
import logging
from typing import Optional, Union, List, Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings

from src.logging_config import get_logger

logger = get_logger(__name__)


class OllamaAdapter:
    """Async adapter for Ollama LLM API."""
    
    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        max_tokens: int = None,
        temperature: float = None,
        timeout: float = None
    ):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.llm_model
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.temperature = temperature or settings.llm_temperature
        self.timeout = timeout if timeout is not None else settings.llm_timeout
        self._client: Optional[httpx.AsyncClient] = None
        
        # Persist initial state
        self._persist_state()
    
    def _persist_state(self):
        """Save current base URL to state file for visibility."""
        import json
        import os
        
        try:
            # Ensure data directory exists
            os.makedirs("data", exist_ok=True)
            
            state = {
                "base_url": self.base_url,
                "updated_at": __import__("datetime").datetime.now().isoformat(),
                "default_model": self.model,
                "extraction_model": settings.llm_extraction_model
            }
            
            with open("data/llm_state.json", "w") as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to persist LLM state: {e}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            # Use a longer timeout for read operations (LLM can be slow)
            # Connect timeout: 10s, read timeout: configured timeout
            timeout_config = httpx.Timeout(
                connect=10.0,
                read=self.timeout,
                write=30.0,
                pool=10.0
            )
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=timeout_config
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def set_base_url(self, new_url: str):
        """
        Update the base URL dynamically (e.g., for Colab tunnels).
        Forces reconnection on next request.
        """
        if new_url != self.base_url:
            logger.info(f"🔄 Updating Ollama base URL: {self.base_url} -> {new_url}")
            self.base_url = new_url
            self._persist_state() # Save new state
            await self.close()  # Close existing client to force recreation with new URL

    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text using Ollama API.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters for the API
            
        Returns:
            Generated text response
        """
        client = await self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
            }
        }
        
        # Dynamic Model Routing
        # Default to configured model (Llama 3.1)
        current_model = self.model
        
        # Detect if this is an entity extraction task
        is_entity_extraction = any(kw in prompt.lower() for kw in ["entity", "extract", "tuple", "relationship"])
        
        if is_entity_extraction:
            # SWITCH TO EXTRACTION MODEL (Qwen 2.5 3B)
            current_model = settings.llm_extraction_model
            logger.info(f"🔄 Routing to Extraction Model: {current_model}")
            
            # 1. Force an "ATS Knowledge Graph Extraction" persona
            if not system_prompt:
                system_prompt = (
                    "You are a precise ATS knowledge graph extraction engine. "
                    "Extract entities and relationships EXACTLY as specified in the schema. "
                    "Output ONLY valid tuples with | delimiter. "
                    "Do NOT add markdown, explanations, or inferred information."
                )
            
            # 2. Configure Strict Options for extraction
            payload["options"] = {
                "temperature": 0.0,      # Absolute determinism
                "num_predict": 2048,     # Reduced window for extraction
                "top_p": 0.1,            # Restrict vocabulary
                "stop": ["\n\n\n", "User:", "Observation:", "Text:"]
            }
        else:
            # USE CHAT MODEL (Llama 3.1 8B)
            logger.info(f"💬 Routing to Chat Model: {current_model}")
            
            # For chat/QA prompts - use more relaxed settings
            payload["options"] = {
                "temperature": 0.1,       # Slight creativity allowed
                "num_predict": 4096,      # Full response length for chat
                "top_p": 0.9,             # Allow more varied vocabulary
                "stop": ["\n\n\n\n", "<|end|>", "</s>"],
                "num_gpu": 999            # Force GPU offloading
            }
            
        # Update payload with routed model
        payload["model"] = current_model
        
        # Override options with kwargs if provided
        for k, v in kwargs.items():
            if k in ["temperature", "max_tokens", "num_gpu"]: 
                continue 

        try:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            result = response.json()
            
            content = result.get("message", {}).get("content", "")
            
            # 🔍 DEBUG: Print raw LLM output for entity extraction (to diagnose format errors)
            if "entity" in prompt.lower() or "extract" in prompt.lower():
                print(f"\n{'='*60}")
                print("🔍 DEBUG: RAW LLM OUTPUT (BEFORE POST-PROCESSING)")
                print(f"{'='*60}")
                print(content[:2000] if len(content) > 2000 else content)
                print(f"{'='*60}\n")
            
            # 4. Post-Processing (The "Safety Net") for Llama 3.1
            if "llama3.1" in self.model:
                 # Clean markdown
                if "```" in content:
                    content = content.replace("```text", "").replace("```", "").strip()
                
                # --- 🛑 CRITICAL FIX: CLEANING LOGIC ---
                import re
                
                # 1. Remove the "Stutter" (e.g., "(entity" appearing inside the value)
                content = re.sub(r'\("entity"\|\s*"?\s*\(entity"?\s*\|', '("entity"|"', content)
                content = re.sub(r'\("relation"\|\s*"?\s*\(relation"?\s*\|', '("relationship"|"', content)
                content = re.sub(r'\("relationship"\|\s*"?\s*\(relationship"?\s*\|', '("relationship"|"', content)

                # 2. Remove standard hallucinations
                content = content.replace("(entity|", "") 
                content = content.replace("(relation|", "")
                content = content.replace("(relationship|", "")
                
                # 3. Remove the ending stop token if it appears
                content = content.replace("</s>", "")
                
                # Fix Double Quotes issues common in Llama 3 (Backup regex)
                content = re.sub(r'^\("entity"\|\s*"?\(entity"?', '("entity"|', content, flags=re.MULTILINE)
                
                # 🔍 DEBUG: Print AFTER post-processing
                if "entity" in prompt.lower() or "extract" in prompt.lower():
                    print(f"\n{'='*60}")
                    print("🔍 DEBUG: LLM OUTPUT (AFTER POST-PROCESSING)")
                    print(f"{'='*60}")
                    print(content[:2000] if len(content) > 2000 else content)
                    print(f"{'='*60}\n")

            logger.debug(f"LLM response length: {len(content)} chars")
            return content
            
        except httpx.TimeoutException as e:
            logger.error(f"Ollama API timeout after {self.timeout}s. Model may be too slow or overloaded.")
            logger.error(f"Consider: 1) Increasing llm_timeout in settings, 2) Using a faster model, 3) Checking Ollama performance")
            raise RuntimeError(f"Ollama request timed out after {self.timeout} seconds. The model may be too slow or the request too complex.") from e
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise
    
    async def check_health(self) -> bool:
        """Check if Ollama is available and model is loaded."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            # Check if our model is available
            if any(self.model in name for name in model_names):
                logger.info(f"✅ Ollama healthy, model '{self.model}' available")
                return True
            else:
                logger.warning(f"Model '{self.model}' not found. Available: {model_names}")
                return False
                
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False



try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


class GeminiAdapter:
    """Async adapter for Google Gemini API."""
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model_name = settings.gemini_model
        
        if not HAS_GEMINI:
            raise RuntimeError("google-generativeai package not installed")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text using Gemini API."""
        try:
            # Gemini doesn't have a separate system prompt param in generate_content
            # typically, so we prepend it or use the system_instruction if initializing (which we aren't here)
            # Efficient pattern: Prepend system prompt to user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System Instruction: {system_prompt}\n\nUser Request: {prompt}"
            
            # Using run_in_executor for async wrapper around sync library
            loop = asyncio.get_running_loop()
            
            # Generation config
            config = genai.types.GenerationConfig(
                temperature=kwargs.get("temperature", settings.llm_temperature),
                max_output_tokens=kwargs.get("max_tokens", settings.llm_max_tokens)
            )
            
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(full_prompt, generation_config=config)
            )
            
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise


# Global adapters
_ollama_adapter: Optional[OllamaAdapter] = None
_gemini_adapter: Optional[GeminiAdapter] = None


def get_ollama_adapter() -> OllamaAdapter:
    """Get or create global Ollama adapter."""
    global _ollama_adapter
    if _ollama_adapter is None:
        _ollama_adapter = OllamaAdapter()
    return _ollama_adapter

def get_gemini_adapter() -> GeminiAdapter:
    """Get or create global Gemini adapter."""
    global _gemini_adapter
    if _gemini_adapter is None:
        _gemini_adapter = GeminiAdapter()
    return _gemini_adapter


async def ollama_llm_func(
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: Optional[List[Dict[str, str]]] = None,
    **kwargs
) -> str:
    """
    LightRAG-compatible LLM function (Universal Dispatcher).
    
    Args:
        prompt: The user prompt
        system_prompt: Optional system prompt
        history_messages: Optional conversation history
        **kwargs: Additional parameters
        
    Returns:
        Generated text response
    """
    provider = settings.llm_provider.lower()
    
    if provider == "gemini":
        adapter = get_gemini_adapter()
        return await adapter.generate(prompt, system_prompt, **kwargs)
    else:
        # Default to Ollama
        adapter = get_ollama_adapter()
        return await adapter.generate(prompt, system_prompt, **kwargs)


# For synchronous contexts
def ollama_llm_func_sync(
    prompt: str,
    system_prompt: Optional[str] = None,
    **kwargs
) -> str:
    """Synchronous wrapper for ollama_llm_func."""
    return asyncio.run(ollama_llm_func(prompt, system_prompt, **kwargs))
