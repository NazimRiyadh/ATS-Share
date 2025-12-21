"""
Comprehensive test for /chat/job endpoint fix.
Tests the complete flow: /analyze -> /chat/job with real API calls.
"""

import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 120.0

async def test_chatjob_with_analyze():
    """Test complete analyze -> chat/job flow."""
    
    print("=" * 70)
    print("COMPREHENSIVE /chat/job ENDPOINT TEST")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    test_results = {
        "health_check": False,
        "analyze": False,
        "chat_job": False,
        "context_used": False,
        "response_complete": False
    }
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        
        # ===== TEST 1: Health Check =====
        print("📋 TEST 1: Health Check")
        try:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✅ Server is healthy")
                print(f"   ✅ RAG: {data.get('components', {}).get('rag', 'unknown')}")
                test_results["health_check"] = True
            else:
                print(f"   ❌ Health check failed: {resp.status_code}")
                return test_results
        except Exception as e:
            print(f"   ❌ Cannot connect to server: {e}")
            print(f"   💡 Make sure server is running: python -m uvicorn api.main:app --reload")
            return test_results
        print()
        
        # ===== TEST 2: Analyze Job =====
        print("📋 TEST 2: Job Analysis (/analyze)")
        job_request = {
            "job_id": "chatjob-test-001",
            "query": "Python developer with AWS, Docker, and PostgreSQL experience. Must have REST API development skills.",
            "top_k": 5
        }
        
        try:
            resp = await client.post(
                f"{BASE_URL}/analyze",
                json=job_request
            )
            
            if resp.status_code == 200:
                data = resp.json()
                candidates_found = data.get("candidates_found", 0)
                candidates = data.get("candidates", [])
                
                print(f"   ✅ Analysis completed")
                print(f"   ✅ Candidates found: {candidates_found}")
                print(f"   ✅ Processing time: {data.get('processing_time', 0):.2f}s")
                
                if candidates:
                    print(f"\n   📋 Top Candidates:")
                    for i, c in enumerate(candidates[:3], 1):
                        print(f"      {i}. {c.get('name')} (Score: {c.get('score', 0):.2%})")
                        print(f"         Skills: {', '.join(c.get('skills_matched', [])[:5])}")
                        print(f"         Reason: {c.get('match_reason', 'N/A')}")
                    
                    test_results["analyze"] = True
                    
                    # Store for later verification
                    analyzed_candidates = candidates
                else:
                    print(f"   ⚠️  No candidates found - this may affect chat test")
                    test_results["analyze"] = True
                    analyzed_candidates = []
            else:
                print(f"   ❌ Analysis failed: {resp.status_code}")
                print(f"   Response: {resp.text[:200]}")
                return test_results
                
        except Exception as e:
            print(f"   ❌ Analysis error: {e}")
            return test_results
        print()
        
        # ===== TEST 3: Chat About Job (THE CRITICAL TEST) =====
        print("📋 TEST 3: Job Chat (/chat/job) - TESTING THE FIX")
        
        chat_queries = [
            "List the top 3 candidates and their key skills",
            "Which candidate has the most relevant experience?",
            "Tell me about Python developers in the results"
        ]
        
        for i, query in enumerate(chat_queries, 1):
            print(f"\n   Query {i}: {query}")
            
            try:
                resp = await client.post(
                    f"{BASE_URL}/chat/job",
                    json={
                        "job_id": "chatjob-test-001",
                        "message": query,
                        "mode": "mix"
                    }
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response", "")
                    mode_used = data.get("mode_used", "unknown")
                    
                    print(f"   ✅ Chat response received")
                    print(f"   ✅ Mode: {mode_used}")
                    print(f"   ✅ Length: {len(response_text)} chars")
                    
                    # CRITICAL CHECKS FOR THE FIX
                    checks_passed = []
                    checks_failed = []
                    
                    # Check 1: Response is not too short
                    if len(response_text) > 50:
                        checks_passed.append("Response has substantial content")
                    else:
                        checks_failed.append(f"Response too short ({len(response_text)} chars)")
                    
                    # Check 2: Response is complete (doesn't end with ':' or incomplete)
                    if not response_text.strip().endswith(':'):
                        checks_passed.append("Response is complete (no trailing ':')")
                    else:
                        checks_failed.append("Response appears truncated (ends with ':')")
                    
                    # Check 3: Response mentions actual candidate names from analysis
                    if analyzed_candidates:
                        candidate_names = [c.get('name', '') for c in analyzed_candidates[:5]]
                        names_mentioned = [name for name in candidate_names if name.lower() in response_text.lower() and len(name) > 3]
                        
                        if names_mentioned:
                            checks_passed.append(f"✨ CONTEXT USED! Mentions candidates: {', '.join(names_mentioned[:3])}")
                            test_results["context_used"] = True
                        else:
                            checks_failed.append("No candidate names from analysis found in response")
                    
                    # Check 4: Response mentions skills from the job query
                    job_skills = ["Python", "AWS", "Docker", "PostgreSQL", "API"]
                    skills_mentioned = [s for s in job_skills if s.lower() in response_text.lower()]
                    
                    if skills_mentioned:
                        checks_passed.append(f"Mentions relevant skills: {', '.join(skills_mentioned)}")
                    
                    # Print checks
                    if checks_passed:
                        for check in checks_passed:
                            print(f"   ✅ {check}")
                    if checks_failed:
                        for check in checks_failed:
                            print(f"   ⚠️  {check}")
                    
                    # Show response preview
                    preview = response_text[:300] + "..." if len(response_text) > 300 else response_text
                    print(f"\n   📝 Response Preview:")
                    print(f"   {preview}")
                    
                    if i == 1:  # First query
                        test_results["chat_job"] = True
                        if not checks_failed:
                            test_results["response_complete"] = True
                    
                else:
                    print(f"   ❌ Chat failed: {resp.status_code}")
                    print(f"   Response: {resp.text[:200]}")
                    
            except Exception as e:
                print(f"   ❌ Chat error: {e}")
        
        print()
    
    # ===== FINAL SUMMARY =====
    print("=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    total_tests = len(test_results)
    passed = sum(test_results.values())
    
    for test_name, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}  {test_name}")
    
    print(f"\n   Score: {passed}/{total_tests} tests passed")
    
    if test_results["context_used"]:
        print("\n   🎉 SUCCESS! The /chat/job fix is working!")
        print("   ✅ Candidates from /analyze are properly passed to chat")
        print("   ✅ LLM is receiving and using the candidate context")
    elif test_results["chat_job"]:
        print("\n   ⚠️  Chat endpoint works but may not be using analyze context")
        print("   Check if candidate names from analysis appear in responses")
    else:
        print("\n   ❌ Tests failed - review errors above")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Save results
    with open("chatjob_test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
    print("\n📁 Results saved to: chatjob_test_results.json")
    
    return test_results


if __name__ == "__main__":
    asyncio.run(test_chatjob_with_analyze())
