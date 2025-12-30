import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_dynamic_config():
    print(f"Testing Dynamic Config at {BASE_URL}...")
    
    # 1. Check Health (should be healthy initially with localhost)
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print(f"Initial Health: {resp.status_code} - {resp.json().get('status')}")
    except Exception as e:
        print(f"❌ Could not connect to API. Is it running? ({e})")
        sys.exit(1)

    # 2. Update URL to a dummy value
    new_url = "http://localhost:12345" # Dummy URL
    print(f"\n🔄 Updating LLM URL to: {new_url}")
    
    resp = requests.post(f"{BASE_URL}/config/llm-url", json={"url": new_url})
    
    if resp.status_code == 200:
        print("✅ Success:", resp.json())
    else:
        print("❌ Failed:", resp.text)
        
    # 3. Check Health again (Ollama might show 'degraded' or 'unreachable' depending on logic, 
    # but the API itself should be up)
    # Note: check_health tries to ping Ollama. Since the new URL is fake, Ollama check should fail.
    print("\nChecking Health after update (Expect 'ollama': False)...")
    resp = requests.get(f"{BASE_URL}/health")
    data = resp.json()
    ollama_status = data.get("components", {}).get("ollama")
    print(f"Health Status: {data.get('status')}")
    print(f"Ollama Component Status: {ollama_status}")
    
    if ollama_status is False:
        print("✅ Verified: Ollama is unreachable at the new dummy URL (as expected).")
    else:
        print("⚠️  Warning: Ollama still reported healthy? Did the URL update stick?")

    # 4. Revert to original (assuming default localhost:11434)
    original_url = "http://localhost:11434"
    print(f"\n🔄 Reverting LLM URL to: {original_url}")
    resp = requests.post(f"{BASE_URL}/config/llm-url", json={"url": original_url})
    print("Revert Response:", resp.json())
    
    # 5. Final Health Check
    time.sleep(1)
    resp = requests.get(f"{BASE_URL}/health")
    data = resp.json()
    if data.get("components", {}).get("ollama") is True:
        print("✅ System fully recovered!")
    else:
        print("❌ System failed to recover connectivity.")

if __name__ == "__main__":
    test_dynamic_config()
