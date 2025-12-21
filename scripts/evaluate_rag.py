import sys
import json
import requests
import statistics
from pathlib import Path
from typing import List, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings

API_URL = f"http://localhost:{settings.api_port}"
GOLDEN_SET_FILE = "data/golden_set.json"

def evaluate():
    print(f"\n==================================================")
    print(f"RAG Evaluation (Golden Set)")
    print(f"==================================================\n")
    
    if not Path(GOLDEN_SET_FILE).exists():
        print(f"❌ Golden set file not found: {GOLDEN_SET_FILE}")
        return

    with open(GOLDEN_SET_FILE, "r") as f:
        test_cases = json.load(f)

    results = []
    
    # Check API health
    try:
        requests.get(f"{API_URL}/health")
    except:
        print(f"❌ API not reachable at {API_URL}. Please start the server.")
        return

    print(f"Running {len(test_cases)} test cases...\n")

    for i, case in enumerate(test_cases, 1):
        query = case["query"]
        expected = [e.lower() for e in case["expected_candidates"]]
        min_expected = case.get("min_expected", 1)
        
        print(f"Test {i}: '{query}'")
        
        # Call API (using Analyze endpoint for pure retrieval)
        try:
            resp = requests.post(
                f"{API_URL}/analyze",
                json={
                    "query": query,
                    "job_id": "eval_job",
                    "top_k": 20
                }
            )
            
            if resp.status_code != 200:
                print(f"  ❌ Error: {resp.status_code}")
                continue
                
            data = resp.json()
            retrieved_names = [c["name"] for c in data.get("candidates", [])]
            retrieved_lower = [n.lower() for n in retrieved_names]
            
            # Calculate metrics
            matches = 0
            matched_names = []
            
            for exp in expected:
                # Fuzzy match or substring match
                found = False
                for ret in retrieved_lower:
                    if exp in ret or ret in exp:
                        matches += 1
                        found = True
                        matched_names.append(ret)
                        break
            
            recall = 1.0 if matches >= min_expected else 0.0
            # Strict recall: matches / len(expected)
            strict_recall = matches / len(expected) if expected else 0
            
            print(f"  Found: {matches}/{len(expected)} expected candidates")
            print(f"  Top Matches: {matched_names}")
            
            results.append({
                "recall": recall,
                "strict_recall": strict_recall,
                "matches": matches
            })
            
        except Exception as e:
            print(f"  ❌ Exception: {e}")

    # Summary
    if results:
        avg_recall = statistics.mean([r["recall"] for r in results])
        avg_strict = statistics.mean([r["strict_recall"] for r in results])
        
        print(f"\n==================================================")
        print(f"Results Summary")
        print(f"==================================================")
        print(f"Total Tests: {len(results)}")
        print(f"Success Rate (Found at least {min_expected}): {avg_recall*100:.1f}%")
        print(f"Average Recall (All expected found): {avg_strict*100:.1f}%")
        print(f"==================================================\n")
    else:
        print("No results to display.")

if __name__ == "__main__":
    evaluate()
