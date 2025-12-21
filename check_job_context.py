"""
Check what job contexts are currently stored.
"""
import httpx
import asyncio

async def check_stored_jobs():
    async with httpx.AsyncClient(timeout=30) as client:
        # Try to get the job context
        job_id = "kg_query_004"
        
        print(f"Checking if job_id '{job_id}' has stored analysis...")
        
        try:
            resp = await client.get(f"http://127.0.0.1:8000/analyze/{job_id}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Found stored analysis!")
                print(f"   Candidates: {data.get('candidates_found', 0)}")
                print(f"   Created: {data.get('created_at', 'unknown')}")
            elif resp.status_code == 404:
                print(f"❌ No stored analysis found for job_id '{job_id}'")
                print(f"\nℹ️  You need to run /analyze first:")
                print(f'   POST /analyze with {{"job_id": "{job_id}", "query": "your job requirements", "top_k": 5}}')
            else:
                print(f"⚠️  Unexpected response: {resp.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_stored_jobs())
