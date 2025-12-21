"""
Test to trigger the debug logging and see what candidates are passed.
"""
import asyncio
import httpx

async def test():
    async with httpx.AsyncClient(timeout=60) as client:
        # Analyze
        print("1. Analyzing for Tammy...")
        resp = await client.post(
            "http://127.0.0.1:8000/analyze",
            json={"job_id": "tammy-test", "query": "Frontend React developer", "top_k": 5}
        )
        data = resp.json()
        candidates = data.get("candidates", [])
        print(f"   Found {len(candidates)} candidates:")
        for c in candidates:
            print(f"   - {c['name']} ({c['score']:.2%})")
        
        # Check if Tammy is in the results
        tammy_in_results = any("tammy" in c['name'].lower() for c in candidates)
        print(f"\n   Tammy in analyze results: {tammy_in_results}")
        
        # Chat
        print("\n2. Chatting about candidates...")
        print("   (Check server logs for debug output)\n")
        resp = await client.post(
            "http://127.0.0.1:8000/chat/job",
            json={"job_id": "tammy-test", "message": "Who are the candidates?"}
        )
        data = resp.json()
        response = data['response']
        
        # Check if Tammy is in response
        tammy_in_response = "tammy" in response.lower()
        print(f"   Tammy in chat response: {tammy_in_response}")
        print(f"\n   Response: {response[:200]}...")

if __name__ == "__main__":
    asyncio.run(test())
