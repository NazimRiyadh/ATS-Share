---
description: Update the LLM backend wire to a new URL (e.g. Colab/ngrok) without restarting
---

# Update LLM Backend URL

Use this workflow when your LLM provider changes location (e.g., a new Google Colab instance with a fresh ngrok URL).

### 1. Identify New URL

Ensure you have the full URL (including protocol), for example:

- `https://1234-56-78-90.ngrok-free.app`

### 2. Send Update Request

Run the following command in PowerShell:

```powershell
$NewUrl = "https://YOUR-NEW-URL-HERE"
curl -X POST "http://localhost:8000/config/llm-url" `
     -H "Content-Type: application/json" `
     -d "{\"url\": \"$NewUrl\"}"
```

### 3. Verify Connection

Check the system health to confirm the new connection is active:

```powershell
curl http://localhost:8000/health
```

Look for `"ollama": true` in the response.
