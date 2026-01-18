import asyncio
import os
import asyncpg
from neo4j import GraphDatabase
from src.config import settings

async def reset_lightrag():
    print("="*50)
    print("LIGHTRAG CACHE RESET")
    print("="*50)
    
    # 1. Clear PostgreSQL (LightRAG tables)
    print("Connecting to PostgreSQL...")
    try:
        dsn = settings.postgres_uri.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn)
        
        # Get all tables starting with lightrag_
        rows = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'lightrag_%'"
        )
        tables = [row['table_name'] for row in rows]
        print(f"Found LightRAG tables: {tables}")
        
        for table in tables:
            await conn.execute(f"TRUNCATE TABLE {table} CASCADE")
            print(f"  Truncated: {table}")
            
        await conn.close()
        print("✅ PostgreSQL cleared!\n")
    except Exception as e:
        print(f"❌ PostgreSQL Error: {e}")

    # 2. Clear Neo4j
    print("Connecting to Neo4j...")
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri, 
            auth=(settings.neo4j_username, settings.neo4j_password)
        )
        with driver.session() as session:
            result = session.run("MATCH (n) DETACH DELETE n")
            summary = result.consume()
            print(f"  Deleted {summary.counters.nodes_deleted} nodes")
        driver.close()
        print("✅ Neo4j cleared!\n")
    except Exception as e:
        print(f"❌ Neo4j Error: {e}")

    print("="*50)
    print("✅ All caches cleared! Ready for fresh ingestion.")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(reset_lightrag())
