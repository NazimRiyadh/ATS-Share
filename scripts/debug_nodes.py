from neo4j import GraphDatabase
from src.config import settings

def main():
    driver = GraphDatabase.driver(
        settings.neo4j_uri, 
        auth=(settings.neo4j_username, settings.neo4j_password)
    )
    
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN n.entity_id as id, labels(n) as l")
        nodes = list(result)
        print(f"Total Nodes Found: {len(nodes)}")
        for r in nodes:
            print(f"ID: {r['id']} | Labels: {r['l']}")
            
    driver.close()

if __name__ == "__main__":
    main()
