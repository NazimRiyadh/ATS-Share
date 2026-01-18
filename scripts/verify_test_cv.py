import asyncio
from neo4j import AsyncGraphDatabase
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import settings

async def verify_test_cv():
    print("="*60)
    print("VERIFYING TEST CV GRAPH DATA")
    print("="*60)
    
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    target_person = "Test User"
    
    async with driver.session() as session:
        # 1. Check if Person exists
        print(f"\nSearching for PERSON: {target_person}...")
        result = await session.run("""
            MATCH (p:base)
            WHERE toLower(p.entity_id) CONTAINS toLower($name)
            RETURN p.entity_id as name, p.entity_type as type, p.description as desc, labels(p) as labels
            LIMIT 5
        """, name="Test User") # Hardcode partial name for safety
        
        records = await result.data()
        
        if not records:
             print(f"❌ '{target_person}' NOT FOUND in graph (checked via CONTAINS 'Test User')!")
             
             # Diagnositc: List ANY person nodes
             print("Diagnostic: First 5 PERSON nodes found:")
             result_diag = await session.run("MATCH (p:base) WHERE p.entity_type = 'PERSON' RETURN p.entity_id LIMIT 5")
             diag_recs = await result_diag.data()
             print(diag_recs)
             
             await driver.close()
             return

        print(f"✅ Found similar nodes:")
        for r in records:
            print(f"  - {r['name']} ({r['type']}) Desc: {r.get('desc', 'N/A')[:50]}")
            if r['name'] == target_person:
                print("  -> EXACT MATCH CONFIRMED")
            
        # Use the first match for relationship check
        target_person = records[0]['name']

        # 2. Check Relationships

        # 2. Check Relationships
        print(f"\nchecking relationships for: {target_person}")
        result = await session.run("""
            MATCH (p:base)-[r]-(t:base)
            WHERE p.entity_id = $name
            RETURN type(r) as rel_type, t.entity_id as target, t.entity_type as target_type
            ORDER BY rel_type, target
        """, name=target_person)
        
        records = await result.data()
        
        expected_entities = {
            "SKILL": ["Python", "Java", "Docker", "Neo4j"], # Flask, PostgreSQL might be there too
            "COMPANY": ["TechCorp"],
            "LOCATION": ["San Francisco"],
            "ROLE": ["Software Engineer", "Senior Developer"],
            "CERTIFICATION": ["AWS Certified Solutions Architect"]
        }
        
        found_data = {}
        print("\nFound Relationships:")
        for r in records:
            print(f"  --[{r['rel_type']}]--> {r['target']} ({r['target_type']})")
            t_type = r['target_type'].upper()
            if t_type not in found_data:
                found_data[t_type] = []
            found_data[t_type].append(r['target'])
            
        # 3. Validation Score
        print("\n" + "-"*30)
        print("MISSING ANALYSIS:")
        
        score = 0
        total = 0
        
        for e_type, expected_list in expected_entities.items():
            found_list = found_data.get(e_type, [])
            # Simple containment check (fuzzy matching would be better but exact is good for base test)
            for expected in expected_list:
                total += 1
                # Check for exact or partial match
                match = any(expected.lower() in f.lower() for f in found_list)
                if match:
                    score += 1
                else:
                    print(f"  ❌ Missing {e_type}: {expected}")
        
        print(f"\nCompleteness Score: {score}/{total}")
        
        if score == total:
             print("✅ PERFECT MATCH for basic entities!")
        elif score >= total * 0.8:
             print("⚠️ GOOD MATCH (some missing details)")
        else:
             print("❌ POOR MATCH (many missing details)")

    await driver.close()

if __name__ == "__main__":
    asyncio.run(verify_test_cv())
