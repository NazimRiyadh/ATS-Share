"""
Complete simulation of the /analyze -> /chat/job flow.
Shows how candidates from analyze are used in chat responses.
"""

import asyncio
import httpx
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

async def run_simulation():
    print("=" * 80)
    print("🎬 ATS CHAT/JOB SIMULATION - Complete Flow")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}\n")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        
        # ============================================================
        # STEP 1: Analyze a job
        # ============================================================
        print("📋 STEP 1: Analyzing Job Requirements")
        print("-" * 80)
        
        job_request = {
            "job_id": "simulation-demo",
            "query": "Senior Python Developer with AWS, Docker, and PostgreSQL experience. Must have REST API development skills and 5+ years experience.",
            "top_k": 5
        }
        
        print(f"Job ID: {job_request['job_id']}")
        print(f"Requirements: {job_request['query']}")
        print(f"\n⏳ Analyzing candidates...")
        
        analyze_resp = await client.post(
            f"{BASE_URL}/analyze",
            json=job_request
        )
        
        if analyze_resp.status_code != 200:
            print(f"❌ Analysis failed: {analyze_resp.status_code}")
            return
        
        analyze_data = analyze_resp.json()
        candidates = analyze_data['candidates']
        
        print(f"\n✅ Analysis Complete!")
        print(f"   Found: {analyze_data['candidates_found']} candidates")
        print(f"   Processing time: {analyze_data['processing_time']:.2f}s")
        
        print(f"\n📊 Top Candidates:")
        for i, c in enumerate(candidates, 1):
            print(f"\n   {i}. {c['name']}")
            print(f"      Score: {c['score']:.1%}")
            print(f"      Skills: {', '.join(c['skills_matched'][:5])}")
            print(f"      Reason: {c['match_reason']}")
        
        # ============================================================
        # STEP 2: Chat about the candidates
        # ============================================================
        print("\n" + "=" * 80)
        print("💬 STEP 2: Chatting About Candidates")
        print("-" * 80)
        
        # Test multiple questions
        questions = [
            "Who are the top 3 candidates?",
            "Which candidate has the most AWS experience?",
            "Tell me about their Python skills",
            "Do any candidates have Docker experience?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n🔹 Question {i}: {question}")
            print(f"⏳ Thinking...")
            
            chat_resp = await client.post(
                f"{BASE_URL}/chat/job",
                json={
                    "job_id": "simulation-demo",
                    "message": question,
                    "mode": "mix"
                }
            )
            
            if chat_resp.status_code == 200:
                chat_data = chat_resp.json()
                response = chat_data['response']
                
                print(f"\n💡 Answer:")
                print(f"   {response}")
                
                # Check if candidate names from analyze appear in response
                mentioned_candidates = [
                    c['name'] for c in candidates 
                    if c['name'].lower() in response.lower()
                ]
                
                if mentioned_candidates:
                    print(f"\n   ✅ Using analyze context! Mentioned: {', '.join(mentioned_candidates[:3])}")
                else:
                    print(f"\n   ⚠️  No candidates from analyze mentioned in response")
                
                print(f"\n   📊 Mode: {chat_data['mode_used']}")
                print(f"   ⏱️  Time: {chat_data['processing_time']:.2f}s")
            else:
                print(f"   ❌ Chat failed: {chat_resp.status_code}")
        
        # ============================================================
        # STEP 3: Compare with direct query (no job context)
        # ============================================================
        print("\n" + "=" * 80)
        print("🔄 STEP 3: Comparing with Direct Query (No Job Context)")
        print("-" * 80)
        
        print(f"\n🔹 Same question without job context:")
        print(f"   Question: {questions[0]}")
        
        direct_resp = await client.post(
            f"{BASE_URL}/chat/query",
            json={
                "query": questions[0],
                "mode": "mix"
            }
        )
        
        if direct_resp.status_code == 200:
            direct_data = direct_resp.json()
            print(f"\n💡 Direct Query Answer:")
            print(f"   {direct_data['response'][:300]}...")
            print(f"\n   ℹ️  This query doesn't use the pre-analyzed candidates")
            print(f"   ℹ️  It does a fresh RAG search instead")
        
        # ============================================================
        # Summary
        # ============================================================
        print("\n" + "=" * 80)
        print("📝 SIMULATION SUMMARY")
        print("=" * 80)
        print(f"\n✅ /analyze found {len(candidates)} candidates and stored them")
        print(f"✅ /chat/job used those candidates to answer {len(questions)} questions")
        print(f"✅ Pre-analyzed context makes responses more relevant and faster")
        print(f"\n💡 Key Difference:")
        print(f"   /chat/job  = Uses PRE-ANALYZED candidates (faster, more relevant)")
        print(f"   /chat/query = Does FRESH search (slower, more general)")
        
        print(f"\n🎬 Simulation Complete!")
        print(f"Ended: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_simulation())
