from neo4j import GraphDatabase
from src.config import settings

def show_graph():
    driver = GraphDatabase.driver(
        settings.neo4j_uri, 
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    print("="*60)
    print("EXTRACTED ENTITIES")
    print("="*60)
    with driver.session() as session:
        # Match any node with a label (assuming 'base' or any other)
        result = session.run("MATCH (n) RETURN n.entity_id as id, n.description as desc, labels(n) as lbl ORDER BY n.entity_id")
        for record in result:
            desc = record["desc"][:80] + "..." if record["desc"] and len(record["desc"]) > 80 else record["desc"] or "No desc"
            labels = [l for l in record["lbl"] if l != 'base'] # Show specific labels
            print(f"  [{record['id']}] ({', '.join(labels)})")
            print(f"       └─ {desc}")

    print("\n" + "="*60)
    print("EXTRACTED RELATIONSHIPS")
    print("="*60)
    with driver.session() as session:
        result = session.run("MATCH (s)-[r]->(t) RETURN s.entity_id as source, type(r) as type, t.entity_id as target, r.description as desc")
        for record in result:
            desc = record["desc"][:60] + "..." if record["desc"] and len(record["desc"]) > 60 else record["desc"] or "No desc"
            print(f"  {record['source']} --[{record['type']}]--> {record['target']}")
            print(f"       └─ {desc}")
            
    driver.close()

if __name__ == "__main__":
    show_graph()
