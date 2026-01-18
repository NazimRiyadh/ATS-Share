import asyncio
import sys
# Make sure src is in path if running as script from root
sys.path.append(".")

from src.services.ingestion_service import ResumeIngestionService

async def main():
    print("Starting Ingestion...")
    print("Starting Ingestion...")
    import lightrag.operate
    print(f"DEBUG: Pre-init parser: {lightrag.operate.split_string_by_multi_markers}")
    s = ResumeIngestionService()
    try:
        r = await s.ingest_single('data/resumes/AI_Engineer_Raghu_10.txt')
        print(f"Ingestion Finished. Success: {r.success}")
    except Exception as e:
        print(f"Ingestion Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
