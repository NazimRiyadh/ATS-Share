"""
ATS STRESS TEST - Principal AI Evaluation Engineer
Tests system with 5 diverse JDs and 5 complex queries.
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List, Any

BASE_URL = "http://127.0.0.1:8000"

# ============================================================
# 5 DISTINCT JOB DESCRIPTIONS
# ============================================================

JOB_DESCRIPTIONS = {
    "JD-001": {
        "title": "Senior Backend Engineer",
        "query": """
Senior Backend Engineer - 5+ years Python experience required.
Requirements: 5+ years of Python development (Django, FastAPI).
Strong experience with PostgreSQL and Redis.
Docker and Kubernetes experience required.
Must NOT have primarily frontend focus.
"""
    },
    
    "JD-002": {
        "title": "Machine Learning Engineer",
        "query": """
Machine Learning Engineer - Production ML Systems.
Requirements: 3+ years ML engineering experience.
Strong Python with TensorFlow or PyTorch.
Experience deploying ML models to production.
"""
    },
    
    "JD-003": {
        "title": "Senior Data Scientist",
        "query": """
Senior Data Scientist - Analytics & Modeling.
Requirements: 4+ years data science experience.
Advanced Python (Pandas, NumPy, Scikit-learn).
SQL proficiency for complex queries.
Data visualization (Tableau, Power BI).
"""
    },
    
    "JD-004": {
        "title": "Java Enterprise Developer",
        "query": """
Senior Java Enterprise Developer.
Requirements: 6+ years Java development (Java 11+).
Spring Boot and Spring Cloud expertise.
Microservices architecture with Kafka.
Must have Java - Python or other languages NOT a substitute.
"""
    },
    
    "JD-005": {
        "title": "DevOps/SRE Engineer",
        "query": """
DevOps/SRE Engineer - Cloud Infrastructure.
Requirements: 4+ years DevOps/SRE experience.
Terraform and Infrastructure as Code.
Kubernetes and container orchestration expert.
"""
    }
}


# ============================================================
# 5 COMPLEX REAL-WORLD QUERIES (Validation Logic)
# ============================================================

COMPLEX_QUERIES = [
    {
        "id": "Q1",
        "name": "Python Backend",
        "required_skills": ["Python"],
        "forbidden_skills": [],
        "expected_matches": ["JD-001", "JD-002", "JD-003"], # All Python-heavy roles
        "must_not_match": [] # Polyglots allowed (Java devs might know Python)
    },
    {
        "id": "Q2", 
        "name": "ML Engineer",
        "required_skills": ["Tensorflow", "Pytorch", "Machine Learning"], # At least one
        "forbidden_skills": [],
        "expected_matches": ["JD-002"],
        "must_not_match": ["JD-004", "JD-005"] # Java and DevOps usually don't do ML
    },
    {
        "id": "Q3",
        "name": "Java Enterprise",
        "required_skills": ["Java", "Spring"],
        "forbidden_skills": [],
        "expected_matches": ["JD-004"],
        "must_not_match": ["JD-003", "JD-005"] # Data Scientist and DevOps usually don't do Java Enterprise
    },
    {
        "id": "Q4",
        "name": "DevOps/SRE",
        "required_skills": ["Kubernetes", "Terraform", "Aws"],
        "forbidden_skills": [],
        "expected_matches": ["JD-005"],
        "must_not_match": ["JD-003", "JD-004"] # Data Scientist / Java Dev usually don't match
    },
    {
        "id": "Q5",
        "name": "Data Science",
        "required_skills": ["Sql", "Tableau", "Pandas", "Data Analysis"],
        "forbidden_skills": [],
        "expected_matches": ["JD-003"],
        "must_not_match": ["JD-004", "JD-002"] # Java candidates generally don't match DS; ML vs DS is fuzzy but we test distinctness
    }
]


async def run_stress_test():
    """Run comprehensive stress test."""
    print("=" * 70)
    print("ATS STRESS TEST - Principal AI Evaluation Engineer")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()
    
    results = {
        "queries_tested": 0,
        "queries_passed": 0,
        "queries_failed": 0,
        "query_results": []
    }
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        
        # Test each query
        for query_spec in COMPLEX_QUERIES:
            query_id = query_spec["id"]
            required = query_spec["required_skills"]
            expected = query_spec["expected_matches"]
            must_not = query_spec["must_not_match"]
            
            print(f"\n{'='*60}")
            print(f"QUERY {query_id}: {query_spec['name']}")
            print(f"{'='*60}")
            print(f"   Required Skills (Any): {required}")
            
            actual_matches = []
            
            # Run against each JD
            for jd_id, jd_spec in JOB_DESCRIPTIONS.items():
                try:
                    # Analyze using the JD
                    resp = await client.post(
                        f"{BASE_URL}/analyze",
                        json={
                            "job_id": f"stress-{jd_id}-{query_id}",
                            "query": jd_spec["query"],
                            "top_k": 5
                        }
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        
                        if not candidates:
                            print(f"   [EMPTY] {jd_id}: No candidates found")
                            continue
                            
                        # Check skills of returned candidates
                        # If ANY returned candidate matches the requirements, we consider the JD "Matched"
                        # (Because in a real search, finding 1 good candidate is a success)
                        candidate_skills = set()
                        for c in candidates:
                            # Normalize skills
                            skills = [s.lower() for s in c.get("skills_matched", [])]
                            candidate_skills.update(skills)
                        
                        # Logic: Does this result match the QUERY requirements?
                        # 1. Must have at least one required skill
                        has_required = any(req.lower() in candidate_skills for req in required)
                        
                        if has_required:
                            actual_matches.append(jd_id)
                            print(f"   [MATCH] {jd_id}: MATCHED (Skills: {list(candidate_skills)[:5]}...)")
                        else:
                            print(f"   [NO MATCH] {jd_id}: No relevant skills (Found: {list(candidate_skills)[:5]}...)")
                            
                    else:
                        print(f"   [ERROR] {jd_id}: Request failed ({resp.status_code})")
                        
                except Exception as e:
                    print(f"   [ERROR] {jd_id}: Error - {str(e)[:50]}")
            
            # Evaluate Verdict
            false_positives = [jd for jd in actual_matches if jd in must_not]
            false_negatives = [jd for jd in expected if jd not in actual_matches]
            
            verdict = "PASS"
            if false_positives or false_negatives:
                verdict = "FAIL"
                results["queries_failed"] += 1
            else:
                results["queries_passed"] += 1
            
            print(f"   VERDICT: {verdict}")
            if false_positives:
                print(f"   False Positives: {false_positives}")
            if false_negatives:
                print(f"   False Negatives: {false_negatives}")
            
            results["queries_tested"] += 1
            results["query_results"].append({
                "id": query_id,
                "verdict": verdict,
                "false_positives": false_positives,
                "false_negatives": false_negatives
            })
    
    # Summary
    print()
    print("=" * 70)
    print("STRESS TEST SUMMARY")
    print("=" * 70)
    print(f"   Queries Tested: {results['queries_tested']}")
    print(f"   Queries Passed: {results['queries_passed']}")
    print(f"   Queries Failed: {results['queries_failed']}")
    
    if results["queries_failed"] == 0:
        print("   OVERALL VERDICT: INDUSTRY-READY")
    else:
        print("   OVERALL VERDICT: NOT INDUSTRY-READY")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_stress_test())
