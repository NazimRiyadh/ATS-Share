"""
Quick test to show the improved response style.
"""

import asyncio
import httpx

BASE_URL = "http://127.0.0.1:8000"

async def test_response_style():
    print("Testing improved chat response style...")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # First analyze
        print("\n1. Running /analyze...")
        analyze_resp = await client.post(
            f"{BASE_URL}/analyze",
            json={
                "job_id": "style-test",
                "query": "Frontend engineer with React and TypeScript",
                "top_k": 3
            }
        )
        
        if analyze_resp.status_code == 200:
            data = analyze_resp.json()
            print(f"   Found {data['candidates_found']} candidates\n")
        
        # Then chat
        print("2. Asking about candidates...")
        chat_resp = await client.post(
            f"{BASE_URL}/chat/job",
            json={
                "job_id": "style-test",
                "message": "Who are the top candidates?",
                "mode": "mix"
            }
        )
        
        if chat_resp.status_code == 200:
            data = chat_resp.json()
            response = data['response']
            
            print("\n" + "=" * 70)
            print("RESPONSE:")
            print("=" * 70)
            print(response)
            print("=" * 70)
            
            # Check for improvement
            print("\n✅ IMPROVEMENTS:")
            if "based on the document chunks" not in response.lower():
                print("   - No more 'based on document chunks' phrasing")
            if "not mentioned" not in response.lower() and "not explicitly mentioned" not in response.lower():
                print("   - No more confusing 'not mentioned' statements")
            if len(response.split('\n')) <= 10:
                print("   - More concise response")
                
            print(f"\n📊 Response length: {len(response)} chars")
            print(f"📊 Mode: {data['mode_used']}")
        else:
            print(f"❌ Chat failed: {chat_resp.status_code}")

if __name__ == "__main__":
    asyncio.run(test_response_style())
