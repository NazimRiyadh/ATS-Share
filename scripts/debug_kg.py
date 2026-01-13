import asyncio
import os
import sys
from pathlib import Path
from neo4j import AsyncGraphDatabase

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import settings

async def debug():
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    async with driver.session() as session:
        print("--- Debugging Nodes from std_test_resume.txt ---")
        result = await session.run("""
            MATCH (n) 
            WHERE n.file_path CONTAINS 'std_test_resume.txt'
            RETURN n.entity_id, n.entity_type, labels(n)
        """)
        records = await result.data()
        if not records:
            print("No nodes found for this file.")
            # Fallback: Check if file_path is somehow wrong, search by keywords
            print("Checking by keyword 'Stanford'...")
            result = await session.run("""
                MATCH (n) WHERE n.entity_id CONTAINS 'Stanford' RETURN n.entity_id, n.entity_type, n.file_path
            """)
            print(await result.data())
        else:
            for r in records:
                print(f"ID: {r['n.entity_id']} | Type: {r['n.entity_type']} | Labels: {r['labels(n)']}")
            
    await driver.close()

if __name__ == "__main__":
    asyncio.run(debug())
