import asyncio
import os
import asyncpg
from tabulate import tabulate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DB config from env or use defaults (matching docker-compose)
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "ats_db")

DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

async def inspect():
    print(f"\n🔌 Connecting to {DSN}...")
    try:
        conn = await asyncpg.connect(DSN)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("Ensure 'docker-compose up -d' is running.")
        return

    print("✅ Connected!\n")

    # 1. List all tables
    print("📋 TABLES IN DATABASE:")
    tables = await conn.fetch("""
        SELECT schemaname, tablename 
        FROM pg_catalog.pg_tables 
        WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';
    """)
    
    # Convert Record objects to simple list of lists
    table_rows = [[r['schemaname'], r['tablename']] for r in tables]
    print(tabulate(table_rows, headers=["Schema", "Table"], tablefmt="simple"))
    print("-" * 40)

    # 2. Check Row Counts & Vector Dimensions
    print("📊 TABLE STATISTICS:")
    stats = []
    
    # Check for known tables (adjust if your schema differs)
    target_tables = ["lightrag_docs", "lightrag_text_chunks", "lightrag_entities", "lightrag_relationships"]
    
    for table in tables:
        t_name = table['tablename']
        try:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {t_name}")
            stats.append([t_name, count])
        except Exception:
            pass
            
    print(tabulate(stats, headers=["Table", "Row Count"], tablefmt="grid"))
    print("-" * 40)

    # 3. Sample Vector Data (if chunks exist)
    print("👀 SAMPLE VECTOR DATA (lightrag_text_chunks):")
    try:
        # Check if table exists
        exists = await conn.fetchval("SELECT to_regclass('lightrag_text_chunks')")
        if exists:
            # Get one row with vector preview
            row = await conn.fetchrow("""
                SELECT substring(content for 50) as snippet, 
                       vector_dims(embedding) as dims 
                FROM lightrag_text_chunks 
                LIMIT 1
            """)
            if row:
                print(f"Snippet: {row['snippet']}...")
                print(f"Vector Dimensions: {row['dims']}")
            else:
                print("Table is empty.")
        else:
            print("Table 'lightrag_text_chunks' not found.")
    except Exception as e:
        print(f"Error reading vectors: {e}")

    await conn.close()

    # 4. Check Neo4j
    print("-" * 40)
    print("🕸️ Neo4j GRAPH DATA:")
    
    from neo4j import GraphDatabase
    
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        print(f"✅ Connected to Neo4j at {NEO4J_URI}")
        
        with driver.session() as session:
            # Count nodes
            node_counts = session.run("""
                MATCH (n) 
                RETURN head(labels(n)) as Label, count(n) as Count 
                ORDER BY Count DESC
            """)
            
            print("\nNode Counts:")
            print(tabulate(node_counts.values(), headers=["Label", "Count"], tablefmt="simple"))
            
            # Count relationships
            rel_counts = session.run("""
                MATCH ()-[r]->() 
                RETURN type(r) as Type, count(r) as Count 
                ORDER BY Count DESC LIMIT 10
            """)
            print("\nTop 10 Relationships:")
            print(tabulate(rel_counts.values(), headers=["Type", "Count"], tablefmt="simple"))
            
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j Error: {e}")


if __name__ == "__main__":
    asyncio.run(inspect())
