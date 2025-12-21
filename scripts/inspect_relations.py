import asyncio
import sys
from pathlib import Path
import asyncpg
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings

async def main():
    uri = settings.postgres_uri.replace("postgresql+asyncpg://", "postgresql://")
    print(f"Connecting to: {uri}")
    conn = await asyncpg.connect(uri)
    
    # 1. Get raw relations
    print("\n[lightrag_relation_chunks] (Top 2)")
    rows = await conn.fetch('SELECT * FROM lightrag_relation_chunks LIMIT 2')
    for r in rows:
        print(r)
        
    relation_entities = set()
    rows = await conn.fetch('SELECT source_entity, target_entity FROM lightrag_relation_chunks')
    for r in rows:
        relation_entities.add(r['source_entity'])
        relation_entities.add(r['target_entity'])
        
    print(f"\nUnique Entities in Relations: {len(relation_entities)}")

    # 2. Get full entities
    print("\n[lightrag_full_entities]")
    full_entities = set()
    rows = await conn.fetch('SELECT entity_name FROM lightrag_full_entities')
    for r in rows:
        full_entities.add(r['entity_name'])
    
    print(f"Full Entities Count: {len(full_entities)}")
    print(f"Sample Full Entities: {list(full_entities)[:5]}")
    
    # 3. Intersection
    missing = relation_entities - full_entities
    print(f"\nEntities in Relations but MISSING from Full: {len(missing)}")
    if missing:
        print(f"Sample Missing: {list(missing)[:5]}")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
