"""
Graph Quality Assessment Script
Analyzes the knowledge graph to verify resume data quality.
"""
import asyncio
from neo4j import AsyncGraphDatabase
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import settings

async def assess_graph():
    print("="*60)
    print("GRAPH QUALITY ASSESSMENT")
    print("="*60)
    
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    async with driver.session() as session:
        # 1. Node Statistics
        print("\n NODE STATISTICS:")
        result = await session.run("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY count DESC
        """)
        records = await result.data()
        for r in records:
            print(f"  {r['label']}: {r['count']}")
        
        # 2. Relationship Statistics
        print("\n RELATIONSHIP STATISTICS:")
        result = await session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
        """)
        records = await result.data()
        for r in records:
            print(f"  {r['type']}: {r['count']}")
        
        # 3. Sample PERSON nodes
        print("\n SAMPLE PERSON NODES (Top 5):")
        result = await session.run("""
            MATCH (p:base)
            WHERE p.entity_type = 'PERSON' OR p.description CONTAINS 'Candidate'
            RETURN p.entity_id as name, p.description as desc
            LIMIT 5
        """)
        records = await result.data()
        if records:
            for r in records:
                print(f"  * {r['name']}: {r['desc'][:50] if r.get('desc') else 'N/A'}...")
        else:
            # Try alternative query
            result = await session.run("""
                MATCH (p:base)
                RETURN p.entity_id as name, p.description as desc
                LIMIT 5
            """)
            records = await result.data()
            for r in records:
                print(f"  * {r['name']}: {r.get('desc', 'N/A')[:50] if r.get('desc') else 'N/A'}...")
        
        # 4. Sample relationships for one person
        print("\n SAMPLE RELATIONSHIPS (First Person Found):")
        result = await session.run("""
            MATCH (p:base)-[r]->(target:base)
            RETURN p.entity_id as person, type(r) as rel_type, target.entity_id as target
            LIMIT 10
        """)
        records = await result.data()
        for r in records:
            print(f"  {r['person']} --[{r['rel_type']}]--> {r['target']}")
        
        # 5. Check for specific skills
        print("\n TOP SKILLS IN GRAPH:")
        result = await session.run("""
            MATCH (s:base)
            WHERE s.entity_id IN ['Python', 'Java', 'SQL', 'AWS', 'Machine Learning', 'Docker', 'Kubernetes']
            RETURN s.entity_id as skill
        """)
        records = await result.data()
        skills_found = [r['skill'] for r in records]
        print(f"  Found: {skills_found if skills_found else 'No common skills found'}")
        
        # 6. Sample candidate with their skills
        print("\n FULL PROFILE (Random Candidate):")
        result = await session.run("""
            MATCH (p:base)-[r]->(t:base)
            WITH p, collect({rel: type(r), target: t.entity_id}) as rels
            RETURN p.entity_id as person, p.description as desc, rels
            LIMIT 1
        """)
        records = await result.data()
        if records:
            rec = records[0]
            print(f"  Name: {rec['person']}")
            print(f"  Description: {rec.get('desc', 'N/A')}")
            print(f"  Relationships:")
            for rel in rec['rels'][:10]:
                print(f"    * {rel['rel']} -> {rel['target']}")
    
    await driver.close()
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(assess_graph())
