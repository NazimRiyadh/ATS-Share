"""
Direct test to verify candidate context is being passed to /chat/job.
Tests at the API handler level to see exactly what data flows through.
"""

import asyncio
import httpx
import json

BASE_URL = "http://127.0.0.1:8000"

async def test_context_passing():
    """Test that candidate context from /analyze is passed to /chat/job."""
    
    print("=" * 70)
    print("DIRECT CONTEXT PASSING TEST")
    print("=" * 70)
    print()
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        
        # Step 1: Analyze a job
        print("Step 1: Running /analyze...")
        analyze_resp = await client.post(
            f"{BASE_URL}/analyze",
            json={
                "job_id": "context-test-001",
                "query": "Senior Python developer with Docker and AWS",
                "top_k": 3
            }
        )
        
        if analyze_resp.status_code != 200:
            print(f"❌ Analyze failed: {analyze_resp.status_code}")
            return
        
        analyze_data = analyze_resp.json()
        candidates = analyze_data.get("candidates", [])
        
        print(f"✅ Found {len(candidates)} candidates")
        print("\nStored Candidates:")
        for i, c in enumerate(candidates, 1):
            print(f"  {i}. {c.get('name')} (Score: {c.get('score', 0):.2%})")
            print(f"     - Match Reason: {c.get('match_reason', 'N/A')}")
            print(f"     - Skills: {', '.join(c.get('skills_matched', []))}")
            print(f"     - Experience: {c.get('experience_summary', 'N/A')}")
            print  ()
        
        # Step 2: Get stored job context
        print("\nStep 2: Retrieving stored job context...")
        get_resp = await client.get(f"{BASE_URL}/analyze/context-test-001")
        
        if get_resp.status_code == 200:
            stored_data = get_resp.json()
            stored_candidates = stored_data.get("candidates", [])
            print(f"✅ Stored context has {len(stored_candidates)} candidates")
            
            # Verify the stored format
            if stored_candidates:
                sample = stored_candidates[0]
                print(f"\nSample stored candidate format:")
                print(f"  Type: {type(sample)}")
                print(f"  Keys: {list(sample.keys()) if isinstance(sample, dict) else 'N/A'}")
                print(f"  Has 'name': {'name' in sample if isinstance(sample, dict) else False}")
                print(f"  Has 'match_reason': {'match_reason' in sample if isinstance(sample, dict) else False}")
                print(f"  Has 'skills_matched': {'skills_matched' in sample if isinstance(sample, dict) else False}")
        else:
            print(f"⚠️  Could not retrieve stored context: {get_resp.status_code}")
        
        # Step 3: Chat with job context
        print("\n" + "=" * 70)
        print("Step 3: Testing /chat/job with stored context...")
        print("=" * 70)
        
        chat_resp = await client.post(
            f"{BASE_URL}/chat/job",
            json={
               "job_id": "context-test-001",
                "message": "Who are the candidates and what are their key skills?",
                "mode": "mix"
            }
        )
        
        if chat_resp.status_code != 200:
            print(f"❌ Chat failed: {chat_resp.status_code}")
            print(f"Error: {chat_resp.text}")
            return
        
        chat_data = chat_resp.json()
        response_text = chat_data.get("response", "")
        
        print(f"\n✅ Chat response received ({len(response_text)} chars)")
        print(f"Mode used: {chat_data.get('mode_used')}")
        print()
        
        # Analysis
        print("=" * 70)
        print("CONTEXT VERIFICATION")
        print("=" * 70)
        
        # Check 1: Do stored candidate names appear in response?
        names_mentioned = []
        for c in candidates:
            name = c.get('name', '')
            if len(name) > 3 and name.lower() in response_text.lower():
                names_mentioned.append(name)
        
        if names_mentioned:
            print(f"✅ CONTEXT USED! Found {len(names_mentioned)} candidate names in response:")
            for name in names_mentioned:
                print(f"   - {name}")
        else:
            print(f"⚠️  WARNING: No stored candidate names found in response")
            print(f"   Stored names were: {[c.get('name') for c in candidates]}")
            print(f"   This could mean:")
            print(f"   1. The LLM retrieved different candidates from RAG (not using stored context)")
            print(f"   2. The stored context wasn't passed to chat_with_dual_retrieval")
        
        # Check 2: Do stored skills appear in response?
        all_stored_skills = set()
        for c in candidates:
            all_stored_skills.update(c.get('skills_matched', []))
        
        skills_mentioned = [s for s in all_stored_skills if s.lower() in response_text.lower()]
        
        if skills_mentioned:
            print(f"\n✅ Found {len(skills_mentioned)} stored skills in response:")
            print(f"   {', '.join(list(skills_mentioned)[:5])}")
        
        # Show response
        print(f"\n{'='*70}")
        print("CHAT RESPONSE:")
        print("=" * 70)
        print(response_text)
        print("=" * 70)
        
        # Save for review
        result = {
            "stored_candidates": candidates,
            "names_mentioned": names_mentioned,
            "skills_mentioned": skills_mentioned,
            "response": response_text,
            "context_used": len(names_mentioned) > 0
        }
        
        with open("context_test_result.json", "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"\n📁 Results saved to: context_test_result.json")
        
        return result


if __name__ == "__main__":
    asyncio.run(test_context_passing())
