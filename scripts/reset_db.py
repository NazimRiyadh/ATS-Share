
import asyncio
import sys
from pathlib import Path
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
import asyncpg
from neo4j import GraphDatabase
import os

async def reset_postgres():
    print("🧹 Cleaning PostgreSQL...")
    try:
        conn = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db
        )
        
        # List of tables to truncate
        # Note: We preserve lightrag_llm_cache to speed up re-ingestion if prompts are identical
        tables = [
            "lightrag_doc_status",
            "lightrag_full_entities",
            "lightrag_full_relations",
            "lightrag_vdb_chunks",
        ]
        
        for table in tables:
            try:
                # Check if table exists first to avoid error spam
                exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table
                )
                if exists:
                    await conn.execute(f"TRUNCATE TABLE {table} CASCADE")
                    print(f"   - Truncated {table}")
                else:
                    print(f"   - Skipped {table} (not found)")
            except Exception as e:
                print(f"   - Error truncating {table}: {e}")
                
        await conn.close()
    except Exception as e:
        print(f"❌ Postgres connection failed: {e}")

def reset_neo4j():
    print("🧹 Cleaning Neo4j...")
    
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri, 
            auth=(settings.neo4j_username, settings.neo4j_password)
        )
        # Use the specific database we configured
        db_name = os.getenv("NEO4J_DATABASE", "neo4j")
        with driver.session(database=db_name) as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("   - All nodes and relationships deleted")
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")

async def main():
    await reset_postgres()
    reset_neo4j()
    print("✨ Reset complete!")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
