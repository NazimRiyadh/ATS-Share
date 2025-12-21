import sys
import time
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings

API_URL = f"http://localhost:{settings.api_port}"
FILE_PATH = "data/resumes/resume_1.pdf" # Ensure this exists or use a robust path

def test_async_ingestion():
    print(f"Testing Async Ingestion at {API_URL}...")
    
    # 1. Check Health
    try:
        resp = requests.get(f"{API_URL}/health")
        if resp.status_code != 200:
            print(f"❌ API unhealthy: {resp.text}")
            return
        print("✅ API is healthy")
    except Exception as e:
        print(f"❌ API not reachable: {e}")
        return

    # 2. Upload Resume
    print(f"\nUploading {FILE_PATH}...")
    if not Path(FILE_PATH).exists():
        # Fallback to finding first txt in data/resumes
        resumes = list(Path("data/resumes").glob("*.txt"))
        if not resumes:
            print("❌ No resume files found in data/resumes")
            return
        upload_file = resumes[0]
    else:
        upload_file = Path(FILE_PATH)
        
    try:
        with open(upload_file, "rb") as f:
            resp = requests.post(
                f"{API_URL}/ingest",
                files={"file": f},
                data={"candidate_name": "Async Test Candidate"}
            )
            
        if resp.status_code != 200:
            print(f"❌ Upload failed: {resp.text}")
            return
            
        data = resp.json()
        task_id = data.get("task_id")
        print(f"✅ Upload successful. Task ID: {task_id}")
        
    except Exception as e:
        print(f"❌ Upload request failed: {e}")
        return
        
    # 3. Poll Status
    print(f"\nPolling status for task {task_id}...")
    start_time = time.time()
    while True:
        try:
            resp = requests.get(f"{API_URL}/ingest/status/{task_id}")
            if resp.status_code != 200:
                print(f"❌ Status check failed: {resp.text}")
                break
                
            status_data = resp.json()
            status = status_data.get("status")
            print(f"Statement: {status}...")
            
            if status == "SUCCESS":
                result = status_data.get("result", {})
                print(f"\n✅ Task Succeeded!")
                print(f"   Candidate: {result.get('candidate_name')}")
                print(f"   Time: {result.get('processing_time')}s")
                break
            elif status == "FAILURE":
                print(f"\n❌ Task Failed!")
                print(f"   Result: {status_data.get('result')}")
                break
            
            if time.time() - start_time > 60:
                print("\n❌ Timeout waiting for task completion")
                break
                
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Polling exception: {e}")
            break

if __name__ == "__main__":
    test_async_ingestion()
