"""Query Neo4j to see all extracted entities and relationships."""
from neo4j import GraphDatabase
import sys
sys.path.insert(0, '.')
from src.config import settings


def main():
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    with driver.session() as session:
        print("=" * 60)
        print("EXTRACTED ENTITIES")
        print("=" * 60)
        
        result = session.run("""
            MATCH (n) 
            RETURN n.entity_id as name, n.entity_type as type, n.description as desc
            ORDER BY n.entity_type, n.entity_id
        """)
        
        for record in result:
            print(f"  [{record['type']}] {record['name']}")
            if record['desc']:
                print(f"       └─ {record['desc'][:80]}")
        
        print()
        print("=" * 60)
        print("EXTRACTED RELATIONSHIPS")
        print("=" * 60)
        
        result = session.run("""
            MATCH (a)-[r]->(b)
            RETURN a.entity_id as source, type(r) as rel_type, b.entity_id as target, r.description as desc
            ORDER BY a.entity_id, type(r)
        """)
        
        for record in result:
            print(f"  {record['source']} --[{record['rel_type']}]--> {record['target']}")
            if record['desc']:
                print(f"       └─ {record['desc'][:60]}")
    
    driver.close()


if __name__ == "__main__":
    main()
