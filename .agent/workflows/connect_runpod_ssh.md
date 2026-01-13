---
description: Connect to a RunPod GPU instance via SSH Tunnel to usage remote Ollama as localhost
---

# Connect to RunPod via SSH Tunnel

Using SSH tunneling allows you to map the remote RunPod Ollama instance to your local `localhost:11434`. This is more secure than public URLs and requires **zero configuration changes** to your local app.

### 1. Prerequisite: RunPod Setup

1.  Start your RunPod instance (e.g., using TheBloke's LLM template or standard Ollama).
2.  Ensure Ollama is running on the pod (usually port `11434`).
3.  Copy the **SSH Command** from the RunPod dashboard (Connect button). It usually looks like:
    `ssh root@123.456.78.90 -p 12345 -i "C:\path\to\keys\id_ed25519"`

### 2. Establish the Tunnel

Add the `-L` flag to forward your local port `11434` to the remote port `11434`.

**PowerShell Command:**

```powershell
# Syntax: ssh -L [LocalPort]:localhost:[RemotePort] [User]@[Host] -p [SSHPort] -i [KeyFile]

ssh -L 11434:localhost:11434 root@<POD_IP> -p <POD_PORT> -i "path/to/private/key"
```

**Example:**

```powershell
ssh -L 11434:localhost:11434 root@38.123.45.67 -p 22022 -i "C:\Users\User\.ssh\id_runpod"
```

_Leave this terminal window open._

### 3. Verify Connection

Open a new terminal and check if you can reach the remote Ollama:

```powershell
curl http://localhost:11434/api/tags
```

If successful, you will see the list of models on the RunPod GPU.

### 4. Run ATS

Now simply run your app as usual. It will think it's talking to a local Ollama instance, but the heavy lifting is happening on the RunPod GPU!

```powershell
python scripts/ingest_resumes.py ...
```
