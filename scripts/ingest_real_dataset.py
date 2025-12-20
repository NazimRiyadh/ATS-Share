import requests
import time

BASE_URL = "http://127.0.0.1:8000"
DATA_DIR = r"D:\KT Informatik\ATS project\Final Version\data\real_resumes"

def ingest_batch():
    print(f"Triggering batch ingestion for {DATA_DIR}...")
    try:
        response = requests.post(
            f"{BASE_URL}/ingest/batch",
            json={
                "directory": DATA_DIR,
                "batch_size": 10
            }
        )
        if response.status_code == 200:
            print("Batch ingestion started/completed successfully:")
            print(response.json())
        else:
            print(f"Failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    ingest_batch()
