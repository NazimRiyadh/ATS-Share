import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.services.ingestion_service import ResumeIngestionService
from src.config import settings

# Sample resume content with new entity types
SAMPLE_RESUME = """
John Doe
Senior Software Engineer
San Francisco, CA

SUMMARY
Experienced engineer with a focus on scalable systems.

EXPERIENCE
Google
Senior Software Engineer | 2018 - Present
- Worked on Project Alpha, a large-scale distributed system.
- Utilized Python and Kubernetes.

EDUCATION
Stanford University
BS Computer Science | 2014 - 2018

SKILLs
Python, Java, Docker, Kubernetes
"""

async def verify():
    print("MATCHing and analyzing verification...")
    # 1. Create a dummy file
    test_file = Path("data/resumes/std_test_resume.txt")
    test_file.parent.mkdir(parents=True, exist_ok=True)
    with open(test_file, "w") as f:
        f.write(SAMPLE_RESUME)
        
    print(f"Created test file: {test_file}")

    # 1.5 Clean up existing data for John Doe
    from neo4j import AsyncGraphDatabase
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    async with driver.session() as session:
        print("Cleaning up old 'John Doe' nodes...")
        await session.run("MATCH (n:base {entity_id: 'John Doe'}) DETACH DELETE n")
    await driver.close()
    
    # 2. Ingest
    service = ResumeIngestionService()
    print("Ingesting resume...")
    # Force ingest to ensure we hit the new code path
    result = await service.ingest_single(str(test_file))
    print(f"Ingestion Result: {result.success} (Time: {result.processing_time:.2f}s)")
    
    if not result.success:
        print(f"Error: {result.error}")
        return

    # 3. Verify in Neo4j
    from neo4j import AsyncGraphDatabase
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    async with driver.session() as session:
        print("\n--- Verification Results ---")
        
        # Check Entity Types (Case Insensitive)
        result = await session.run("""
            MATCH (n) 
            WHERE toUpper(n.entity_type) IN ['PROJECT', 'EDUCATION', 'INDUSTRY', 'SKILL', 'ROLE']
            RETURN n.entity_id, n.entity_type
        """)
        records = await result.data()
        print(f"Found {len(records)} new entity types (PROJECT/EDUCATION):")
        for r in records:
            print(f"  - [{r['n.entity_type']}] {r['n.entity_id']}")
            
        # Check Source Tracking (file_path)
        # We need to find the node for John Doe
        result = await session.run("""
            MATCH (n:base {entity_id: 'John Doe'})
            RETURN n
        """)
        record = await result.single()
        if record:
            node = record['n']
            print("\nSource Tracking Check for 'John Doe':")
            props = dict(node)
            file_path = props.get('file_path')
            print(f"  file_path: {file_path}")
            if "std_test_resume.txt" in str(file_path):
                print("  ✅ PASS: File path correctly tracked.")
            else:
                print(f"  ❌ FAIL: File path mismatch or missing. Got: {file_path}")
        else:
            print("  ❌ FAIL: 'John Doe' node not found.")

    await driver.close()

if __name__ == "__main__":
    asyncio.run(verify())
