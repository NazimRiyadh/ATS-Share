"""
Quick verification script for ingestion and mix mode.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
from src.logging_config import get_logger, configure_logging

configure_logging()
logger = get_logger(__name__)

async def test_ingestion():
    """Test ingestion with a single resume."""
    print("\n" + "="*60)
    print("STEP 1: Testing Resume Ingestion")
    print("="*60)
    
    from src.ingestion import ingest_resume
    from src.rag_config import get_rag_manager
    
    # Initialize RAG
    print("Initializing RAG...")
    manager = get_rag_manager()
    await manager.initialize()
    print("✅ RAG initialized")
    
    # Find a test resume
    test_dir = Path("data/test_resume")
    if test_dir.exists():
        files = list(test_dir.glob("*.txt")) + list(test_dir.glob("*.pdf"))
        if files:
            test_file = str(files[0])
            print(f"Ingesting: {test_file}")
            result = await ingest_resume(test_file)
            if result.success:
                print(f"✅ Ingestion successful: {result.candidate_name}")
            else:
                print(f"❌ Ingestion failed: {result.error}")
                return False
        else:
            print("No test files found")
            return False
    else:
        print("Test directory not found")
        return False
    
    return True


async def test_db_counts():
    """Check database row counts."""
    print("\n" + "="*60)
    print("STEP 2: Checking Database State")
    print("="*60)
    
    import asyncpg
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    DB_USER = os.getenv("POSTGRES_USER", "postgres")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
    DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB", "ats_db")
    
    DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    try:
        conn = await asyncpg.connect(DSN)
        print("✅ Connected to PostgreSQL")
        
        # Check key tables
        tables = ["lightrag_docs", "lightrag_text_chunks", "lightrag_entities", "lightrag_relationships"]
        
        for table in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                print(f"  {table}: {count} rows")
            except Exception as e:
                print(f"  {table}: Table not found or error - {e}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_mix_mode():
    """Test mix mode query."""
    print("\n" + "="*60)
    print("STEP 3: Testing Mix Mode Query")
    print("="*60)
    
    from src.rag_config import get_rag_manager
    from lightrag import QueryParam
    
    manager = get_rag_manager()
    rag = await manager.initialize()
    
    queries = [
        "Find Python developers",
        "Who has Java experience?",
        "List all candidates"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        try:
            response = await rag.aquery(query, param=QueryParam(mode="mix"))
            # Truncate long responses
            if len(response) > 300:
                response = response[:300] + "..."
            print(f"Response: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return True


async def main():
    """Run all verification tests."""
    print("\n" + "#"*60)
    print("# ATS System Verification")
    print("#"*60)
    
    try:
        # Test 1: Database check
        await test_db_counts()
        
        # Test 2: Mix mode
        await test_mix_mode()
        
        print("\n" + "="*60)
        print("VERIFICATION COMPLETE")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
