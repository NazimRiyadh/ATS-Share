"""
Script to reset LightRAG caches in PostgreSQL and Neo4j.
Run this for a completely fresh ingestion.
"""

import asyncio
from neo4j import GraphDatabase
import asyncpg

# Import settings
import sys
sys.path.insert(0, '.')
from src.config import settings


async def clear_postgres():
    """Clear LightRAG tables in PostgreSQL."""
    print("Connecting to PostgreSQL...")
    try:
        conn = await asyncpg.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            user=settings.postgres_user,
            password=settings.postgres_password,
            database=settings.postgres_db
        )
        
        # Check what tables exist
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' AND tablename LIKE 'lightrag%'
        """)
        print(f"Found LightRAG tables: {[t['tablename'] for t in tables]}")
        
        # Truncate each table
        for table in tables:
            tablename = table['tablename']
            await conn.execute(f'TRUNCATE TABLE {tablename} CASCADE')
            print(f"  Truncated: {tablename}")
        
        await conn.close()
        print("✅ PostgreSQL cleared!")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")
        return False


def clear_neo4j():
    """Clear all nodes and relationships in Neo4j."""
    print("\nConnecting to Neo4j...")
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password)
        )
        
        with driver.session() as session:
            # Get count before
            result = session.run("MATCH (n) RETURN count(n) as cnt")
            before = result.single()["cnt"]
            
            # Delete all
            session.run("MATCH (n) DETACH DELETE n")
            
            print(f"  Deleted {before} nodes")
        
        driver.close()
        print("✅ Neo4j cleared!")
        return True
    except Exception as e:
        print(f"❌ Neo4j error: {e}")
        return False


async def main():
    print("=" * 50)
    print("LIGHTRAG CACHE RESET")
    print("=" * 50)
    
    pg_ok = await clear_postgres()
    neo_ok = clear_neo4j()
    
    print("\n" + "=" * 50)
    if pg_ok and neo_ok:
        print("✅ All caches cleared! Ready for fresh ingestion.")
    else:
        print("⚠️ Some caches failed to clear. Check errors above.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
