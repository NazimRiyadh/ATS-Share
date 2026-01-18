import asyncio
import os
from src.rag_config import get_rag
from neo4j import GraphDatabase
from src.config import settings

async def test_insert():
    print("Initializing LightRAG...")
    rag = await get_rag()
    
    # Mock Payload (Perfect Format)
    mock_extraction_output = """
entity###TestCandidate###PERSON###Candidate Name
entity###TestSkill_Python###SKILL###Programming Language
entity###TestSkill_Java###SKILL###Programming Language
relationship###TestCandidate###HAS_SKILL###TestSkill_Python###Known skill
relationship###TestCandidate###HAS_SKILL###TestSkill_Java###Known skill
"""
    
    print("\n--- Mocking LLM Output ---")
    print(mock_extraction_output.strip())
    print("--------------------------")

    # Override LLM function to return mock data
    async def mock_llm_func(prompt, system_prompt=None, **kwargs):
        # Return mock data ONLY for extraction prompts
        if "entity" in prompt.lower() or "extract" in prompt.lower():
            return mock_extraction_output
        return "Summary of the document."

    rag.llm_model_func = mock_llm_func
    
    print("Running rag.ainsert('Dummy Content') ...")
    await rag.ainsert("This is a dummy document content to trigger extraction.")
    
    print("Insert complete. Checking Neo4j...")
    
    # Verify in Neo4j
    driver = GraphDatabase.driver(
        settings.neo4j_uri, 
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    with driver.session() as session:
        result = session.run("MATCH (n) WHERE n.entity_id STARTS WITH 'Test' RETURN n.entity_id as id, labels(n) as l")
        nodes = list(result)
        
        print(f"\nFound {len(nodes)} Test Nodes:")
        found_ids = [r['id'] for r in nodes]
        for r in nodes:
            print(f"ID: {r['id']} | Labels: {r['l']}")
            
        expected = ["TestCandidate", "TestSkill_Python", "TestSkill_Java"]
        missing = [e for e in expected if e not in found_ids]
        
        if missing:
            print(f"\n❌ LightRAG FAILED to insert: {missing}")
        else:
            print("\n✅ LightRAG Insertion WORKING correctly for clean data.")

    driver.close()

if __name__ == "__main__":
    asyncio.run(test_insert())
