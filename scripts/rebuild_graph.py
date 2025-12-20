"""
Clean up Neo4j and PostgreSQL databases, then re-ingest all resumes.
This script performs a full graph rebuild with improved prompts.
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()


async def clear_neo4j():
    """Clear all nodes and relationships from Neo4j."""
    from neo4j import AsyncGraphDatabase
    
    driver = AsyncGraphDatabase.driver(
        os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        auth=('neo4j', os.getenv('NEO4J_PASSWORD', 'password'))
    )
    
    try:
        async with driver.session() as session:
            # Get counts before
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            node_count = record['count'] if record else 0
            
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            rel_count = record['count'] if record else 0
            
            print(f"📊 Current Neo4j state: {node_count} nodes, {rel_count} relationships")
            
            # Clear all data
            print("🗑️ Clearing Neo4j database...")
            await session.run("MATCH (n) DETACH DELETE n")
            
            print("✅ Neo4j cleared")
            
    finally:
        await driver.close()


async def clear_postgres_lightrag():
    """Clear LightRAG tables in PostgreSQL."""
    import asyncpg
    
    DB_USER = os.getenv("POSTGRES_USER", "postgres")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
    DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB", "ats_db")
    
    DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    try:
        conn = await asyncpg.connect(DSN)
        print("📊 Connected to PostgreSQL")
        
        # Tables to clear (LightRAG tables)
        tables = [
            "lightrag_doc_full",
            "lightrag_doc_chunks",
            "lightrag_doc_status",
            "lightrag_vdb_chunks",
            "lightrag_vdb_entity",
            "lightrag_vdb_relation",
            "lightrag_full_entities",
            "lightrag_full_relations",
            "lightrag_entity_chunks",
            "lightrag_relation_chunks",
            "lightrag_llm_cache",
            "lightrag_kv_store",
        ]
        
        for table in tables:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                await conn.execute(f"TRUNCATE TABLE {table} CASCADE")
                print(f"  ✅ Cleared {table} ({count} rows)")
            except Exception as e:
                print(f"  ⚠️ {table}: {e}")
        
        await conn.close()
        print("✅ PostgreSQL LightRAG tables cleared")
        
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")
        raise


async def reingest_resumes():
    """Re-ingest all resumes from the data directory."""
    from src.ingestion import ingest_resumes_from_directory
    from src.rag_config import get_rag_manager
    
    resume_dir = Path("data/resumes")
    if not resume_dir.exists():
        print(f"❌ Resume directory not found: {resume_dir}")
        return False
    
    # Count resumes
    resume_files = list(resume_dir.glob("*.txt")) + list(resume_dir.glob("*.pdf"))
    print(f"\n📁 Found {len(resume_files)} resumes to ingest")
    
    # Initialize RAG
    print("🔧 Initializing RAG system...")
    manager = get_rag_manager()
    await manager.initialize()
    print("✅ RAG initialized")
    
    # Run ingestion
    print("\n🚀 Starting ingestion with improved prompts...\n")
    result = await ingest_resumes_from_directory(
        directory=str(resume_dir),
        batch_size=3  # Parallel execution for speed (Qwen 3B)
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"  Total files: {result.total_files}")
    print(f"  Successful: {result.successful}")
    print(f"  Failed: {result.failed}")
    print(f"  Time: {result.total_time:.2f}s")
    
    if result.failed > 0:
        print("\n⚠️ Failed files:")
        for r in result.results:
            if not r.success:
                print(f"  - {r.file_path}: {r.error}")
    
    return result.failed == 0


async def verify_graph():
    """Verify the rebuilt graph quality."""
    from neo4j import AsyncGraphDatabase
    
    driver = AsyncGraphDatabase.driver(
        os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        auth=('neo4j', os.getenv('NEO4J_PASSWORD', 'password'))
    )
    
    try:
        async with driver.session() as session:
            print("\n" + "=" * 60)
            print("GRAPH VERIFICATION")
            print("=" * 60)
            
            # Node count
            result = await session.run("MATCH (n) RETURN count(n) as count")
            record = await result.single()
            node_count = record['count'] if record else 0
            
            # Relationship count
            result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            rel_count = record['count'] if record else 0
            
            # Orphan count
            result = await session.run("""
                MATCH (n) WHERE NOT (n)-[]-() RETURN count(n) as count
            """)
            record = await result.single()
            orphan_count = record['count'] if record else 0
            
            orphan_pct = (orphan_count / node_count * 100) if node_count > 0 else 0
            
            print(f"  📊 Total nodes: {node_count}")
            print(f"  🔗 Total relationships: {rel_count}")
            print(f"  ⚠️ Orphaned nodes: {orphan_count} ({orphan_pct:.1f}%)")
            
            # Check entity types
            print("\n  📋 Entity types:")
            result = await session.run("""
                MATCH (n:base)
                RETURN n.entity_type as type, count(*) as count
                ORDER BY count DESC LIMIT 10
            """)
            async for record in result:
                print(f"    {record['type']}: {record['count']}")
            
            # Success criteria
            if orphan_pct < 20:
                print("\n✅ Graph quality: GOOD (orphans < 20%)")
            else:
                print(f"\n⚠️ Graph quality: NEEDS IMPROVEMENT (orphans: {orphan_pct:.1f}%)")
                
    finally:
        await driver.close()


async def main():
    """Main cleanup and rebuild process."""
    print("\n" + "#" * 60)
    print("# KNOWLEDGE GRAPH FULL REBUILD")
    print("#" * 60)
    
    try:
        # Step 1: Clear Neo4j
        print("\n📌 STEP 1: Clearing Neo4j...")
        await clear_neo4j()
        
        # Step 2: Clear PostgreSQL LightRAG tables
        print("\n📌 STEP 2: Clearing PostgreSQL LightRAG tables...")
        await clear_postgres_lightrag()
        
        # Step 3: Re-ingest resumes
        print("\n📌 STEP 3: Re-ingesting resumes with improved prompts...")
        success = await reingest_resumes()
        
        # Step 4: Verify
        print("\n📌 STEP 4: Verifying graph quality...")
        await verify_graph()
        
        print("\n" + "#" * 60)
        print("# REBUILD COMPLETE")
        print("#" * 60)
        
    except Exception as e:
        print(f"\n❌ Rebuild failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
