"""
Database initialization script.
Verifies connections and initializes LightRAG storages.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncpg
from neo4j import AsyncGraphDatabase


async def check_postgres():
    """Check PostgreSQL connection and pgvector extension."""
    from src.config import settings
    
    print("Checking PostgreSQL...")
    
    try:
        # Parse connection string
        conn = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db
        )
        
        # Check pgvector extension
        result = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        
        if not result:
            print("📦 Creating pgvector extension...")
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        
        # Get version
        version = await conn.fetchval("SELECT version()")
        print(f"✅ PostgreSQL connected: {version[:50]}...")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")
        return False


async def check_neo4j():
    """Check Neo4j connection."""
    from src.config import settings
    
    print("Checking Neo4j...")
    
    try:
        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password)
        )
        
        async with driver.session() as session:
            result = await session.run("RETURN 1 as n")
            record = await result.single()
            
            if record and record["n"] == 1:
                print("✅ Neo4j connected")
        
        await driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Neo4j error: {e}")
        return False


async def check_ollama():
    """Check Ollama availability."""
    from src.llm_adapter import get_ollama_adapter
    
    print("Checking Ollama...")
    
    try:
        adapter = get_ollama_adapter()
        healthy = await adapter.check_health()
        
        if healthy:
            print("✅ Ollama healthy with model available")
        else:
            print("⚠️ Ollama running but model may need to be pulled")
        
        return healthy
        
    except Exception as e:
        print(f"❌ Ollama error: {e}")
        return False


async def initialize_rag():
    """Initialize LightRAG storages."""
    from src.rag_config import get_rag_manager
    
    print("Initializing LightRAG...")
    
    try:
        manager = get_rag_manager()
        await manager.initialize()
        print("✅ LightRAG storages initialized")
        return True
        
    except Exception as e:
        print(f"❌ LightRAG initialization error: {e}")
        return False


async def main():
    """Run all initialization checks."""
    print("\n" + "="*50)
    print("LightRAG ATS - Database Initialization")
    print("="*50 + "\n")
    
    results = {
        "PostgreSQL": await check_postgres(),
        "Neo4j": await check_neo4j(),
        "Ollama": await check_ollama(),
    }
    
    # Only initialize RAG if databases are ready
    if results["PostgreSQL"] and results["Neo4j"]:
        results["LightRAG"] = await initialize_rag()
    else:
        print("\nWARNING: Skipping LightRAG init - databases not ready")
        results["LightRAG"] = False
    
    # Summary
    print("\n" + "="*50)
    print("Initialization Summary")
    print("="*50)
    
    for component, status in results.items():
        icon = "OK" if status else "FAIL"
        print(f"  {icon} - {component}")
    
    all_healthy = all(results.values())
    print("\n" + ("All systems ready!" if all_healthy else "Some components need attention"))
    
    return all_healthy


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
