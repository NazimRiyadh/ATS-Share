import requests
import json
import time

BASE_URL = "http://localhost:8000"

def run_workflow():
    print("🚀 Starting End-to-End Chat Workflow Test")
    print("-" * 50)

    # 1. Analyze a new Job (This triggers Retrieval + LLM Analysis)
    print("\n1️⃣  Analyzing Job Description...")
    job_query = "We are looking for a Senior Cloud Engineer with experience in AWS, Kubernetes, and Python. Leadership skills are a plus."
    
    payload_analyze = {
        "query": job_query,
        "job_id": "test_job_runpod_01",
        "top_k": 5,
        "mode": "mix"
    }
    
    try:
        t0 = time.time()
        resp_analyze = requests.post(f"{BASE_URL}/analyze", json=payload_analyze)
        duration = time.time() - t0
        
        if resp_analyze.status_code == 200:
            data = resp_analyze.json()
            print(f"✅ Analysis Complete ({duration:.2f}s)")
            print(f"   Candidates Found: {len(data.get('candidates', []))}")
            if data.get('candidates'):
                top_candidate = data['candidates'][0]
                print(f"   Top Candidate: {top_candidate.get('name')} (Score: {top_candidate.get('relevance_score')})")
        else:
            print(f"❌ Analysis Failed: {resp_analyze.text}")
            return
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # 2. Chat about the Job (This triggers Context Retrieval + LLM Chat)
    print("\n2️⃣  Chatting about Candidates...")
    chat_question = "Which candidate has the strongest leadership experience?"
    
    payload_chat = {
        "job_id": "test_job_runpod_01",
        "message": chat_question,
        "mode": "mix"
    }
    
    try:
        t0 = time.time()
        resp_chat = requests.post(f"{BASE_URL}/chat/job", json=payload_chat)
        duration = time.time() - t0
        
        if resp_chat.status_code == 200:
            data = resp_chat.json()
            print(f"✅ Chat Response Received ({duration:.2f}s)")
            print(f"   Response: {data.get('response')}")
            print(f"   Sources: {len(data.get('sources', []))}")
        else:
            print(f"❌ Chat Failed: {resp_chat.text}")
            
    except Exception as e:
        print(f"❌ Chat Error: {e}")

    # 3. Direct Query (No Job Context)
    print("\n3️⃣  Direct Knowledge Graph Query...")
    direct_query = "List 3 common skills found in Data Scientist resumes."
    
    payload_query = {
        "query": direct_query,
        "mode": "local"
    }
    
    try:
        t0 = time.time()
        resp_query = requests.post(f"{BASE_URL}/chat/query", json=payload_query)
        duration = time.time() - t0
        
        if resp_query.status_code == 200:
            data = resp_query.json()
            print(f"✅ Query Response Received ({duration:.2f}s)")
            print(f"   Response: {data.get('response')}")
        else:
            print(f"❌ Query Failed: {resp_query.text}")
            
    except Exception as e:
        print(f"❌ Query Error: {e}")

if __name__ == "__main__":
    run_workflow()
