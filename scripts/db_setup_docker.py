
import asyncio
import asyncpg
import sys

# Docker Config (confirmed working)
config = {
    'user': 'postgres',
    'password': 'admin',
    'host': '127.0.0.1',
    'port': 5432
}

async def setup_database():
    print("🔌 Connecting to 'postgres' database...")
    # Connect to default 'postgres' db to manage databases
    sys_conn = await asyncpg.connect(database='postgres', **config)
    
    # Check if 'ats_resume' exists
    exists = await sys_conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'ats_resume'")
    if not exists:
        print("🛠️ Database 'ats_resume' not found. Creating it...")
        await sys_conn.execute('CREATE DATABASE ats_resume')
        print("✅ Database 'ats_resume' created!")
    else:
        print("✅ Database 'ats_resume' already exists.")
    
    await sys_conn.close()

async def setup_schema_for_db(db_name):
    print(f"\n🔌 Connecting to '{db_name}' database...")
    # Connect to target db
    config_copy = config.copy()
    conn = await asyncpg.connect(database=db_name, **config_copy)
    
    print("📜 Running schema setup script...")
    with open('scripts/setup_postgres.sql', 'r') as f:
        sql = f.read()
        
    # Split by statements (simple split by ;) - actually asyncpg execute can handle blocks usually
    # But let's just run the whole thing if it's compatible
    # Removing "--" comments might be safer for simple execution
    try:
        await conn.execute(sql)
        print(f"✅ Schema created successfully in {db_name}!")
    except Exception as e:
        print(f"⚠️ Schema setup warning in {db_name}: {e}")

    await conn.close()
    return True

async def main():
    try:
        # Create ats_resume if missing
        await setup_database()
        
        # Apply schema to ats_resume
        print("\n--- Setup ats_resume ---")
        await setup_schema_for_db('ats_resume')
        
        # Apply schema to ats_db (if exists) just in case config points there
        print("\n--- Setup ats_db ---")
        try:
           await setup_schema_for_db('ats_db')
        except Exception as e:
           print(f"Skipping ats_db: {e}")

        print("\n🎉 ALL DONE! PostgreSQL is ready to use.")
        return True
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        return False

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
