"""
Knowledge Graph Repair Script
Deletes relationship-type nodes (HAS_SKILL, HAS_ROLE, etc.) that were incorrectly created as entities.
Also cleans up UNKNOWN type nodes.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from neo4j import AsyncGraphDatabase
from src.config import settings

# Relationship types that should NOT exist as entities
RELATIONSHIP_TYPES = {'HAS_SKILL', 'HAS_ROLE', 'WORKED_AT', 'LOCATED_IN', 
                      'HAS_CERTIFICATION', 'EDUCATED_AT', 'WORKED_ON', 'IN_INDUSTRY',
                      'REQUIRES_SKILL', 'RELATED_TO', 'HAS_EDUCATION'}

async def repair():
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    async with driver.session() as session:
        print("=== KG Repair Script ===\n")
        
        # 1. Delete relationship type nodes
        print("--- Deleting relationship-type nodes ---")
        for rel_type in RELATIONSHIP_TYPES:
            result = await session.run("""
                MATCH (n) WHERE n.entity_id = $rel_type
                DETACH DELETE n
                RETURN count(n) as deleted
            """, rel_type=rel_type)
            data = await result.single()
            if data and data['deleted'] > 0:
                print(f"  Deleted '{rel_type}' node: {data['deleted']}")
        
        # 2. Delete all UNKNOWN type nodes
        print("\n--- Deleting UNKNOWN type nodes ---")
        result = await session.run("""
            MATCH (n) WHERE n.entity_type = 'UNKNOWN'
            DETACH DELETE n
            RETURN count(n) as deleted
        """)
        data = await result.single()
        print(f"  Deleted UNKNOWN nodes: {data['deleted']}")
        
        # 3. Final stats
        print("\n=== Post-Repair Stats ===")
        result = await session.run("""
            MATCH (n) 
            RETURN n.entity_type as t, count(*) as cnt 
            ORDER BY cnt DESC
        """)
        types = await result.data()
        total = 0
        for t in types:
            print(f"  {t['t']}: {t['cnt']}")
            total += t['cnt']
        print(f"\nTotal nodes: {total}")
        
        # 4. Check relationship count
        result = await session.run("MATCH ()-[r]->() RETURN count(r) as cnt")
        data = await result.single()
        print(f"Total relationships: {data['cnt']}")
    
    await driver.close()
    print("\n✅ Repair complete!")

if __name__ == "__main__":
    asyncio.run(repair())
