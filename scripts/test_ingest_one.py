import asyncio
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag_config import get_rag_manager

# Load env variables
load_dotenv()

async def test_one_resume():
    print("🚀 Starting Single Resume Ingestion Test...")
    
    # Initialize RAG
    manager = get_rag_manager()
    rag = await manager.initialize()
    
    # Define a test resume text
    test_resume = """
    RESUME
    Name: Test User John Doe
    Email: john.doe@test.com
    Location: San Francisco, CA

    PROFESSIONAL SUMMARY
    Software Engineer with 5 years of experience in Python and JavaScript.

    EXPERIENCE
    Software Engineer at Google (2020-2024)
    - Built backend services using Python and Django
    - Implemented REST APIs

    SKILLS
    Python, JavaScript, SQL, AWS, Docker

    CERTIFICATIONS
    AWS Solutions Architect
    """
    
    print("\n📄 Ingesting single resume...")
    try:
        # We wrap it in a list as a insert expects text or list of texts? 
        # ainsert definition: async def ainsert(self, string_or_strings: Union[str, List[str]])
        await rag.ainsert(test_resume)
        print("✅ Ingestion call completed.")
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        return

    print("\n🔍 Verifying Neo4j Storage...")
    from neo4j import AsyncGraphDatabase
    
    driver = AsyncGraphDatabase.driver(
        os.getenv('NEO4J_URI'),
        auth=('neo4j', os.getenv('NEO4J_PASSWORD'))
    )
    
    async with driver.session() as session:
        # Count nodes
        r = await session.run("MATCH (n) RETURN count(n) as count")
        rec = await r.single()
        print(f"  Nodes: {rec['count']}")
        
        # Count relationships
        r = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rec = await r.single()
        print(f"  Relationships: {rec['count']}")
        
        if rec['count'] > 0:
            print("✅ SUCCESS! Entities and relationships were stored.")
        else:
            print("❌ FAILURE! No relationships stored.")

    await driver.close()

if __name__ == "__main__":
    asyncio.run(test_one_resume())
