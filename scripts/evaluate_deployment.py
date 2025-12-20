"""
Deployment Readiness Evaluation Script.
Tests all API endpoints and validates responses.
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"


async def run_evaluation():
    """Run comprehensive deployment evaluation."""
    print("=" * 60)
    print("🚀 ATS DEPLOYMENT READINESS EVALUATION")
    print("=" * 60)
    print(f"Started: {datetime.now().isoformat()}")
    print()
    
    results = {
        "tests_passed": 0,
        "tests_failed": 0,
        "details": []
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        
        # ===== TEST 1: Health Check =====
        print("📋 TEST 1: Health Check")
        try:
            start = time.time()
            resp = await client.get(f"{BASE_URL}/health")
            elapsed = time.time() - start
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✅ Status: {data.get('status')}")
                print(f"   ✅ RAG: {data.get('components', {}).get('rag')}")
                print(f"   ✅ Ollama: {data.get('components', {}).get('ollama')}")
                print(f"   ⏱️  Response time: {elapsed:.2f}s")
                results["tests_passed"] += 1
                results["details"].append({"test": "health", "status": "PASS"})
            else:
                print(f"   ❌ Failed: {resp.status_code}")
                results["tests_failed"] += 1
                results["details"].append({"test": "health", "status": "FAIL"})
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["tests_failed"] += 1
        print()
        
        # ===== TEST 2: Analyze Endpoint =====
        print("📋 TEST 2: Job Analysis (/analyze)")
        try:
            start = time.time()
            resp = await client.post(
                f"{BASE_URL}/analyze",
                json={
                    "job_id": "eval-001",
                    "query": "Python developer with AWS and SQL experience",
                    "top_k": 5
                }
            )
            elapsed = time.time() - start
            
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                print(f"   ✅ Candidates found: {data.get('candidates_found')}")
                print(f"   ✅ Processing time: {data.get('processing_time', 0):.2f}s")
                
                # Check candidate format
                if candidates:
                    c = candidates[0]
                    print(f"   ✅ Candidate format OK:")
                    print(f"      - name: {c.get('name', 'N/A')}")
                    print(f"      - score: {c.get('score', 'N/A')}")
                    print(f"      - match_reason: {c.get('match_reason', 'N/A')}")
                    print(f"      - skills_matched: {c.get('skills_matched', [])}")
                
                results["tests_passed"] += 1
                results["details"].append({"test": "analyze", "status": "PASS", "candidates": len(candidates)})
            else:
                print(f"   ❌ Failed: {resp.status_code} - {resp.text}")
                results["tests_failed"] += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["tests_failed"] += 1
        print()
        
        # ===== TEST 3: Chat Job Endpoint =====
        print("📋 TEST 3: Job Chat (/chat/job)")
        try:
            start = time.time()
            resp = await client.post(
                f"{BASE_URL}/chat/job",
                json={
                    "job_id": "eval-001",
                    "message": "List the top candidates with their skills"
                }
            )
            elapsed = time.time() - start
            
            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "")
                print(f"   ✅ Response length: {len(response_text)} chars")
                print(f"   ✅ Mode used: {data.get('mode_used')}")
                print(f"   ✅ Processing time: {data.get('processing_time', 0):.2f}s")
                
                # Check for incomplete response
                if response_text.endswith(":"):
                    print(f"   ⚠️  WARNING: Response may be truncated (ends with ':')")
                    results["details"].append({"test": "chat_job", "status": "WARN", "issue": "truncated"})
                else:
                    print(f"   ✅ Response complete")
                    results["details"].append({"test": "chat_job", "status": "PASS"})
                
                # Show preview
                preview = response_text[:200] + "..." if len(response_text) > 200 else response_text
                print(f"   📝 Preview: {preview}")
                
                results["tests_passed"] += 1
            else:
                print(f"   ❌ Failed: {resp.status_code}")
                results["tests_failed"] += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["tests_failed"] += 1
        print()
        
        # ===== TEST 4: Direct Query Endpoint =====
        print("📋 TEST 4: Direct Query (/chat/query)")
        try:
            start = time.time()
            resp = await client.post(
                f"{BASE_URL}/chat/query",
                json={
                    "query": "Who has experience with databases?"
                }
            )
            elapsed = time.time() - start
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✅ Response length: {len(data.get('response', ''))} chars")
                print(f"   ✅ Processing time: {data.get('processing_time', 0):.2f}s")
                results["tests_passed"] += 1
                results["details"].append({"test": "direct_query", "status": "PASS"})
            else:
                print(f"   ❌ Failed: {resp.status_code}")
                results["tests_failed"] += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["tests_failed"] += 1
        print()
        
        # ===== TEST 5: Get Job Analysis =====
        print("📋 TEST 5: Get Stored Analysis (/analyze/{job_id})")
        try:
            resp = await client.get(f"{BASE_URL}/analyze/eval-001")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"   ✅ Retrieved job: {data.get('job_id')}")
                print(f"   ✅ Candidates stored: {data.get('candidates_found')}")
                results["tests_passed"] += 1
                results["details"].append({"test": "get_analysis", "status": "PASS"})
            else:
                print(f"   ❌ Failed: {resp.status_code}")
                results["tests_failed"] += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["tests_failed"] += 1
        print()
        
        # ===== TEST 6: API Docs =====
        print("📋 TEST 6: API Documentation (/docs)")
        try:
            resp = await client.get(f"{BASE_URL}/docs")
            if resp.status_code == 200:
                print(f"   ✅ Swagger UI accessible")
                results["tests_passed"] += 1
                results["details"].append({"test": "docs", "status": "PASS"})
            else:
                print(f"   ❌ Failed: {resp.status_code}")
                results["tests_failed"] += 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results["tests_failed"] += 1
        print()
    
    # ===== SUMMARY =====
    print("=" * 60)
    print("📊 EVALUATION SUMMARY")
    print("=" * 60)
    total = results["tests_passed"] + results["tests_failed"]
    print(f"   Tests Passed: {results['tests_passed']}/{total}")
    print(f"   Tests Failed: {results['tests_failed']}/{total}")
    
    if results["tests_failed"] == 0:
        print("\n   ✅ DEPLOYMENT READY!")
    else:
        print(f"\n   ⚠️  {results['tests_failed']} issue(s) to fix before deployment")
    
    print(f"\nCompleted: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Save results
    with open("evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n📁 Results saved to: evaluation_results.json")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_evaluation())
