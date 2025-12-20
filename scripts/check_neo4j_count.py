import asyncio
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from src.config import settings

def main():
    print("Checking Neo4j content...")
    
    uri = settings.neo4j_uri
    user = settings.neo4j_username
    password = settings.neo4j_password
    database = "neo4j" # Forced in rag_config
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session(database=database) as session:
            # Count nodes
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()["count"]
            print(f"Nodes: {node_count}")
            
            # Count relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]
            print(f"Relationships: {rel_count}")
            
            # Sample some labels
            if node_count > 0:
                result = session.run("MATCH (n) RETURN distinct labels(n) as labels LIMIT 5")
                print("Sample Labels:")
                for r in result:
                    print(f" - {r['labels']}")

        driver.close()
    except Exception as e:
        print(f"Error checking Neo4j: {e}")

if __name__ == "__main__":
    main()
