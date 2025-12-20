import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion import ingest_resume
from src.rag_config import get_rag_manager, get_query_param
from src.config import settings

async def verify_ingestion():
    resume_path = os.path.abspath("data/real_resumes/AI_Engineer_1.txt")
    print(f"--- 1. Ingesting {resume_path} ---")
    
    try:
        result = await ingest_resume(resume_path)
        if result.success:
            print(f"[SUCCESS] Ingestion Successful for {result.candidate_name}")
        else:
            print(f"[FAILED] Ingestion Failed: {result.error}")
            return
    except Exception as e:
        print(f"[CRASH] Crash during ingestion: {e}")
        return

    print("\n--- 2. Verifying Graph Entities (Neo4j) ---")
    # We can use the RAG instance to query, or direct Neo4j driver if we had it.
    # LightRAG doesn't expose a direct "get_entities" easily, but we can query the graph storage if accessible.
    
    try:
        rag_manager = get_rag_manager()
        rag = await rag_manager.initialize()
        
        # Using a global query mode might retrieve relevant entities if we search for the candidate name or skills
        query = "List all skills and roles found in the resume"
        print(f"Querying RAG: '{query}'")
        
        # Use 'local' mode to focus on specific entities
        response = await rag.aquery(query, param=get_query_param("local"))
        print(f"\n--- RAG Response (Local Mode) ---\n{response}")
        
    except Exception as e:
        print(f"[FAILED] Verification failed: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_ingestion())
