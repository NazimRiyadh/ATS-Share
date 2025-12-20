import asyncio
import os
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

load_dotenv()

async def cleanup_unknown():
    print("🧹 Starting cleanup of UNKNOWN nodes...")
    
    uri = os.getenv('NEO4J_URI')
    auth = ('neo4j', os.getenv('NEO4J_PASSWORD'))
    driver = AsyncGraphDatabase.driver(uri, auth=auth)
    
    async with driver.session() as session:
        # 1. Count UNKNOWN labeled nodes
        r = await session.run("MATCH (n) WHERE 'UNKNOWN' IN labels(n) RETURN count(n) as c")
        count_labels = (await r.single())['c']
        print(f"found {count_labels} nodes with 'UNKNOWN' label.")
        
        # 2. Count nodes with name "UNKNOWN_CANDIDATE" or similar
        r = await session.run("MATCH (n) WHERE n.id CONTAINS 'UNKNOWN' RETURN count(n) as c")
        count_names = (await r.single())['c']
        print(f"Found {count_names} nodes with 'UNKNOWN' in name.")
        
        # 3. Delete UNKNOWN labels
        if count_labels > 0:
            print("Deleting nodes with 'UNKNOWN' label...")
            await session.run("MATCH (n) WHERE 'UNKNOWN' IN labels(n) DETACH DELETE n")
            print("✅ Deleted UNKNOWN label nodes.")
            
        # 4. Delete UNKNOWN names (optional - asking strictly for 'unknown nodes' usually means labels)
        # But if prompt generated "UNKNOWN_CANDIDATE" typed as PERSON, we might want to keep it or delete it?
        # User complained about "600 unknown nodes". Likely garbage.
        # I'll delete nodes where id is EXACTLY "UNKNOWN" or "UNKNOWN_CANDIDATE" just to be safe.
        
        print("Deleting garbage nodes (id='UNKNOWN' or 'UNKNOWN_CANDIDATE')...")
        await session.run("MATCH (n) WHERE n.id IN ['UNKNOWN', 'UNKNOWN_CANDIDATE'] DETACH DELETE n")
        print("✅ Garbage names deleted.")
        
        # 5. Final Stats
        r = await session.run("MATCH (n) RETURN count(n) as c")
        total = (await r.single())['c']
        print(f"Final Node Count: {total}")

    await driver.close()

if __name__ == "__main__":
    asyncio.run(cleanup_unknown())
