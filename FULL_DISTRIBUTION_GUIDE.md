# Full Distribution Guide (Including venv)

## Creating the Zip

Since you're including everything, just zip the entire folder:

```powershell
# Option 1: Using Windows Explorer
# Right-click on ATS-Share folder → Send to → Compressed folder

# Option 2: Using PowerShell
Compress-Archive -Path D:\ATS-Share\* -DestinationPath ATS-Share-Full.zip -Force
```

**⚠️ Important**: Exclude `.env` (contains YOUR passwords!)

- Delete or rename `.env` to `.env.backup` before zipping
- The `.env.example` will be included

**Zip size**: ~1.3-1.5GB (includes venv)

---

## Team Setup (Super Simple!)

### Prerequisites

Your team needs:

1. **Python 3.12** (MUST be same version as yours!)
   ```bash
   python --version  # Must show 3.12.x
   ```
2. **Docker Desktop**
3. **Ollama** with models:
   ```bash
   ollama pull llama3.1:8b
   ollama pull qwen2.5:3b
   ```

### Setup Steps (5 minutes)

```bash
# 1. Extract zip
# 2. Navigate to folder
cd ATS-Share

# 3. Copy environment file
copy .env.example .env

# 4. Activate venv (already included!)
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# 5. Start databases
docker-compose up -d postgres neo4j redis

# 6. Initialize database
python scripts/init_db.py

# 7. Start API
uvicorn api.main:app --reload

# 8. Test
# Open http://localhost:8000/health
```

---

## Important Notes

### ✅ Advantages

- No `pip install` needed (saves 15 minutes)
- Same package versions guaranteed
- Very simple setup

### ⚠️ Critical Requirements

- **Python version MUST match** (3.12.x)
- **OS compatibility**: Windows venv may not work on Mac/Linux
- **Large file**: Upload/download takes time

### 🔧 If venv doesn't work on team's machine

They can recreate it:

```bash
# Delete old venv
Remove-Item venv -Recurse -Force

# Create new venv
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## What's Included in Your Zip

- ✅ All source code
- ✅ Virtual environment (venv) - 1.2GB
- ✅ Data and configs
- ✅ Documentation
- ❌ `.env` (you must exclude this!)

---

## Quick Checklist

Before zipping:

- [ ] Rename `.env` to `.env.backup` (don't include your passwords!)
- [ ] Verify `venv/` folder exists
- [ ] Create zip

To share:

- [ ] Upload zip (1.3GB)
- [ ] Tell team: "Python 3.12 required, see TEAM_SETUP.md"
