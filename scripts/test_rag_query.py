import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag_config import get_rag, QueryParam

async def test_query():
    print("Initializing LightRAG...")
    rag = await get_rag()
    
    print("\nQuerying: 'Who has Python skills?'")
    result = await rag.aquery("Who has Python skills?", param=QueryParam(mode="mix"))
    
    print("\n" + "="*50)
    print("RESULT:")
    print("="*50)
    print(result[:1000] if len(result) > 1000 else result)

if __name__ == "__main__":
    asyncio.run(test_query())
