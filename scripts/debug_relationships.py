"""
Debug script to inspect relationship structure in the Knowledge Graph.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from neo4j import AsyncGraphDatabase
from src.config import settings

async def debug_relationships():
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    async with driver.session() as session:
        print("=== Relationship Structure Debug ===\n")
        
        # 1. Check relationships from PERSON nodes
        print("--- Relationships FROM PERSON nodes ---")
        result = await session.run("""
            MATCH (a)-[r]->(b) 
            WHERE a.entity_type = 'PERSON'
            RETURN a.entity_id as src, type(r) as rel_type, 
                   r.keywords as keywords, b.entity_id as tgt, b.entity_type as tgt_type
            LIMIT 10
        """)
        records = await result.data()
        for r in records:
            print(f"  {r['src']} --[{r['rel_type']}]--> {r['tgt']} ({r['tgt_type']}) | keywords: {r['keywords']}")
        
        # 2. Check relationships where PERSON is target
        print("\n--- Relationships TO PERSON nodes ---")
        result = await session.run("""
            MATCH (a)-[r]->(b) 
            WHERE b.entity_type = 'PERSON'
            RETURN a.entity_id as src, a.entity_type as src_type, 
                   type(r) as rel_type, r.keywords as keywords, b.entity_id as tgt
            LIMIT 10
        """)
        records = await result.data()
        for r in records:
            print(f"  {r['src']} ({r['src_type']}) --[{r['rel_type']}]--> {r['tgt']} | keywords: {r['keywords']}")
        
        # 3. Check if HAS_SKILL exists as entity
        print("\n--- Check if HAS_SKILL/HAS_ROLE are entities ---")
        result = await session.run("""
            MATCH (n) WHERE n.entity_id IN ['HAS_SKILL', 'HAS_ROLE', 'WORKED_AT']
            RETURN n.entity_id, n.entity_type, labels(n)
        """)
        records = await result.data()
        for r in records:
            print(f"  Found '{r['n.entity_id']}' as entity with type: {r['n.entity_type']}")
        
        if records:
            print("\n  ⚠️ PROBLEM: Relationship types are being stored as entities!")
            print("  This indicates the LLM is outputting wrong tuple format.")
        
    await driver.close()

if __name__ == "__main__":
    asyncio.run(debug_relationships())
