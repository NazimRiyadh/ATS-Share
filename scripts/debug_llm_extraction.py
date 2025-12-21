import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_adapter import get_ollama_adapter
from src.prompts import ATS_ENTITY_EXTRACTION_PROMPT
from src.config import settings

SAMPLE_TEXT = """
Jane Doe
Software Engineer
San Francisco, CA

Experience:
Google - Senior Developer
Jan 2020 - Present
- Used Python and Kubernetes to build scalable APIs.
- Mentored junior engineers.

Microsoft - Junior Developer
2018 - 2020
- Worked with C# and Azure.
"""

async def test_extraction():
    print(f"Testing extraction with model: {settings.llm_model}")
    print(f"Extraction model setting: {settings.llm_extraction_model}")
    
    adapter = get_ollama_adapter()
    
    input_text = SAMPLE_TEXT
    prompt = ATS_ENTITY_EXTRACTION_PROMPT.format(input_text=input_text)
    
    print("\nSending prompt to LLM (this may take 30s)...")
    try:
        response = await adapter.generate(
            prompt=prompt,
            max_tokens=2048,
            temperature=0.0
        )
        
        print("\n" + "="*50)
        print("LLM RESPONSE")
        print("="*50)
        print(response)
        print("="*50)
        
        # Check for relations
        relations = [line for line in response.split('\n') if "relationship" in line]
        print(f"\nFound {len(relations)} relationships.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
