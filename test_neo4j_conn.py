"""Quick test of Neo4j connection using environment variables."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

neo4j_uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

print(f"Testing Neo4j connection...")
print(f"URI: {neo4j_uri}")
print(f"Username: {neo4j_user}")
print(f"Password: {'*' * len(neo4j_password)} (length: {len(neo4j_password)})")

try:
    from neo4j import GraphDatabase
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    with driver.session() as session:
        result = session.run("RETURN 1 as num")
        record = result.single()
        print(f"\n✅ Connection successful! Result: {record['num']}")
        
    driver.close()
    print("✅ Test passed!")
    
except Exception as e:
    print(f"\n❌ Connection failed: {e}")
    print(f"Error type: {type(e).__name__}")
