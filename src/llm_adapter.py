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


def clean_extraction_output(text: str) -> str:
    """
    Clean LLM entity extraction output by removing commentary and keeping only valid tuples.
    
    LLMs sometimes add notes like "Note: I followed the format..." at the end.
    This function strips those and keeps only valid entity/relationship lines.
    """
    if not text:
        return text
    
    lines = text.strip().split('\n')
    valid_lines = []
    
    # Reserved words that should NOT be entities
    RESERVED_RELATIONSHIPS = {
        "HAS_SKILL", "HAS_ROLE", "WORKED_AT", "HAS_CERTIFICATION", 
        "LOCATED_IN", "EDUCATED_AT", "WORKED_ON", "REQUIRES_SKILL", 
        "RELATED_TO", "IN_INDUSTRY", "UNKNOWN", "NONE"
    }

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        current_line = None
        
        # Keep only lines that start with entity or relationship
        if line.lower().startswith('entity###') or line.lower().startswith('relationship###'):
            current_line = line
        # Also handle variations (some LLMs add quotes or parens)
        elif line.startswith('"entity"###') or line.startswith("'entity'###"):
            current_line = 'entity###' + line.split('###', 1)[1]
        elif line.startswith('"relationship"###') or line.startswith("'relationship'###"):
            current_line = 'relationship###' + line.split('###', 1)[1]
        elif line.startswith('("entity"###') or line.startswith("('entity'###"):
            cleaned = line.lstrip('(').lstrip('"\'')
            if cleaned.startswith('entity###'):
                current_line = cleaned.rstrip(')')
        elif line.startswith('("relationship"###') or line.startswith("('relationship'###"):
            cleaned = line.lstrip('(').lstrip('"\'')
            if cleaned.startswith('relationship###'):
                current_line = cleaned.rstrip(')')
        
        if current_line:
            # Smart Filter: Check for reserved keywords
            try:
                parts = current_line.split("###")
                is_valid = True
                
                if current_line.lower().startswith("entity###") and len(parts) >= 2:
                    name = parts[1].strip().upper()
                    if name in RESERVED_RELATIONSHIPS or "->" in parts[1] or "─" in parts[1]:
                        is_valid = False
                        
                elif current_line.lower().startswith("relationship###") and len(parts) >= 4:
                    # relationship###src###rel###tgt
                    src = parts[1].strip().upper()
                    tgt = parts[3].strip().upper()
                    
                    # If source or target is a reserved relationship word, SKIP IT
                    if src in RESERVED_RELATIONSHIPS or tgt in RESERVED_RELATIONSHIPS:
                        is_valid = False
                    
                    # If source or target contains arrow (hallucination), SKIP IT
                    if "->" in parts[1] or "->" in parts[3]:
                        is_valid = False
                
                if is_valid:
                    valid_lines.append(current_line)
            except:
                pass
    
    return '\n'.join(valid_lines)


class RunPodAdapter:
    """Async adapter for RunPod Serverless API."""
    
    def __init__(self):
        self.api_key = settings.runpod_api_key
        self.endpoint_id = settings.runpod_endpoint_id
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout
        
        if not self.api_key:
            raise ValueError("RUNPOD_API_KEY not set")
        if not self.endpoint_id:
            raise ValueError("RUNPOD_ENDPOINT_ID not set")
        
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}"
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=self.timeout, write=30.0, pool=10.0),
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Generate text using RunPod Serverless API (SvenBrnn template format)."""
        client = await self._get_client()
        
        # Build messages array (compatible with SvenBrnn's runpod-worker-ollama)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare input for RunPod handler (SvenBrnn format)
        # CRITICAL: Include model name to use the correct model!
        payload = {
            "input": {
                "model": self.model,  # Use configured model (e.g., llama3.1:8b)
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", settings.llm_temperature),
                    "num_predict": kwargs.get("max_tokens", settings.llm_max_tokens)
                }
            }
        }
        
        try:
            # Submit job to RunPod
            logger.info(f"🚀 Submitting job to RunPod endpoint: {self.endpoint_id}")
            response = await client.post(f"{self.base_url}/run", json=payload)
            response.raise_for_status()
            job_data = response.json()
            job_id = job_data.get("id")
            
            if not job_id:
                raise RuntimeError(f"RunPod did not return job ID: {job_data}")
            
            # Poll for completion
            logger.info(f"⏳ Waiting for RunPod job: {job_id}")
            max_polls = int(self.timeout / 2)  # Poll every 2 seconds
            
            for _ in range(max_polls):
                await asyncio.sleep(2)
                
                status_response = await client.get(f"{self.base_url}/status/{job_id}")
                status_data = status_response.json()
                status = status_data.get("status")
                
                if status == "COMPLETED":
                    output = status_data.get("output", {})
                    if isinstance(output, dict) and "error" in output:
                        raise RuntimeError(f"RunPod error: {output['error']}")
                    logger.info(f"✅ RunPod job completed: {job_id}")
                    
                    # Debug: Log raw output type and structure
                    logger.debug(f"Raw output type: {type(output)}")
                    logger.debug(f"Raw output: {str(output)[:500]}")
                    
                    if isinstance(output, str):
                        return output
                    elif isinstance(output, dict):
                        # OpenAI format: {'choices': [{'message': {'content': '...'}}]}
                        if "choices" in output and output["choices"]:
                            choice = output["choices"][0]
                            if isinstance(choice, dict):
                                message = choice.get("message", {})
                                if isinstance(message, dict) and "content" in message:
                                    logger.debug(f"Extracted content from OpenAI format")
                                    return message["content"]
                        # Fallback formats
                        return output.get("message", {}).get("content", "") or \
                               output.get("response", "") or \
                               output.get("content", "") or \
                               output.get("output", "") or \
                               str(output)
                    elif isinstance(output, list):
                        # Aggregated responses (return_aggregate_stream=True)
                        parts = []
                        for chunk in output:
                            if isinstance(chunk, dict) and "choices" in chunk:
                                for choice in chunk.get("choices", []):
                                    # Non-streaming format: 'message' with 'content'
                                    message = choice.get("message", {})
                                    if isinstance(message, dict) and "content" in message:
                                        parts.append(message["content"])
                                    # Streaming format: 'delta' with 'content'
                                    delta = choice.get("delta", {})
                                    if isinstance(delta, dict) and "content" in delta:
                                        parts.append(delta["content"])
                            elif isinstance(chunk, str):
                                parts.append(chunk)
                        result = "".join(parts)
                        logger.debug(f"Extracted from list: {len(result)} chars")
                        return result
                    else:
                        return str(output)
                
                elif status == "FAILED":
                    error = status_data.get("error", "Unknown error")
                    raise RuntimeError(f"RunPod job failed: {error}")
                
                elif status in ["IN_QUEUE", "IN_PROGRESS"]:
                    continue
                else:
                    logger.warning(f"Unknown RunPod status: {status}")
            
            raise TimeoutError(f"RunPod job timed out after {self.timeout}s")
            
        except httpx.HTTPError as e:
            logger.error(f"RunPod API error: {e}")
            raise


# Global adapters
_ollama_adapter: Optional[OllamaAdapter] = None
_gemini_adapter: Optional[GeminiAdapter] = None
_runpod_adapter: Optional[RunPodAdapter] = None


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

def get_runpod_adapter() -> RunPodAdapter:
    """Get or create global RunPod adapter."""
    global _runpod_adapter
    if _runpod_adapter is None:
        _runpod_adapter = RunPodAdapter()
    return _runpod_adapter


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
    elif provider == "runpod":
        logger.info(f"🚀 Using RunPod provider for LLM request")
        adapter = get_runpod_adapter()
        result = await adapter.generate(prompt, system_prompt, **kwargs)
        
        # Post-process: Clean entity extraction output (strip LLM commentary)
        # Only apply if this looks like an entity extraction prompt
        if "entity###" in prompt.lower() or "relationship###" in prompt.lower():
            result = clean_extraction_output(result)
            logger.debug(f"Cleaned extraction output: {len(result)} chars")
        
        return result
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
