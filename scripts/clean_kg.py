"""
Knowledge Graph Cleanup Script
Removes/fixes malformed entity types and normalizes them.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from neo4j import AsyncGraphDatabase
from src.config import settings

# Valid canonical entity types (uppercase)
VALID_TYPES = {'PERSON', 'SKILL', 'COMPANY', 'ROLE', 'LOCATION', 
               'CERTIFICATION', 'EDUCATION', 'PROJECT', 'INDUSTRY'}

# Mapping from malformed types to canonical types
TYPE_FIXES = {
    'descriptionnotprovided': None,  # Delete these nodes
    '#skill': 'SKILL',
    'documenttype': None,  # Delete
    'event': None,  # Delete if not ATS-relevant
    'unknown': None,  # Delete
}

async def cleanup():
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    async with driver.session() as session:
        print("=== KG Cleanup Script ===")
        
        # 1. Get all entity types
        result = await session.run("""
            MATCH (n) 
            RETURN DISTINCT n.entity_type as t, count(*) as cnt 
            ORDER BY cnt DESC
        """)
        types = await result.data()
        print(f"\nCurrent entity types ({len(types)}):")
        for t in types:
            status = "OK" if t['t'] and t['t'].upper() in VALID_TYPES else "FIX"
            print(f"  [{status}] {t['t']}: {t['cnt']}")
        
        # 2. Normalize lowercase types to uppercase
        print("\n--- Normalizing lowercase types to UPPERCASE ---")
        for valid_type in VALID_TYPES:
            result = await session.run(f"""
                MATCH (n) WHERE n.entity_type = $lower
                SET n.entity_type = $upper
                RETURN count(n) as fixed
            """, lower=valid_type.lower(), upper=valid_type)
            data = await result.single()
            if data and data['fixed'] > 0:
                print(f"  Normalized {valid_type.lower()} -> {valid_type}: {data['fixed']} nodes")
        
        # 3. Fix known malformed types
        print("\n--- Fixing malformed types ---")
        for bad_type, fix in TYPE_FIXES.items():
            if fix is None:
                # Delete these nodes
                result = await session.run("""
                    MATCH (n) WHERE n.entity_type = $t
                    DETACH DELETE n
                    RETURN count(n) as deleted
                """, t=bad_type)
                data = await result.single()
                if data and data['deleted'] > 0:
                    print(f"  DELETED {bad_type}: {data['deleted']} nodes")
            else:
                # Remap to correct type
                result = await session.run("""
                    MATCH (n) WHERE n.entity_type = $bad
                    SET n.entity_type = $good
                    RETURN count(n) as fixed
                """, bad=bad_type, good=fix)
                data = await result.single()
                if data and data['fixed'] > 0:
                    print(f"  Fixed {bad_type} -> {fix}: {data['fixed']} nodes")
        
        # 4. Delete nodes with entity_id = "Description Not Provided"
        print("\n--- Removing placeholder nodes ---")
        result = await session.run("""
            MATCH (n) WHERE n.entity_id = 'Description Not Provided'
            DETACH DELETE n
            RETURN count(n) as deleted
        """)
        data = await result.single()
        if data and data['deleted'] > 0:
            print(f"  Deleted 'Description Not Provided' nodes: {data['deleted']}")
        
        # 5. Final stats
        print("\n=== Post-Cleanup Stats ===")
        result = await session.run("""
            MATCH (n) 
            RETURN n.entity_type as t, count(*) as cnt 
            ORDER BY cnt DESC
        """)
        types = await result.data()
        for t in types:
            print(f"  {t['t']}: {t['cnt']}")
    
    await driver.close()
    print("\n✅ Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(cleanup())
