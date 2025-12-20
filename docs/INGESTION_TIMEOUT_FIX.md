# Ingestion Timeout Issue - Fixed

## Problem Identified

The ingestion process was **failing due to Ollama LLM timeouts** during entity extraction. The diagnostic revealed:

### Symptoms
- ✅ RAG initialization: Working
- ✅ Database connections: Working  
- ✅ Ollama health check: Passing
- ✅ Embedding model: Loading successfully
- ❌ **Ingestion failing**: Ollama ReadTimeout after 120 seconds

### Root Cause

The Ollama LLM adapter had a **120-second timeout** which was insufficient for:
1. Entity extraction from resumes (complex processing)
2. Knowledge graph construction (multiple LLM calls)
3. Large documents requiring extensive processing

The `qwen2.5:7b` model can take longer than 2 minutes to process complex entity extraction prompts, especially on CPU.

## Fixes Applied

### 1. Increased LLM Timeout (src/config.py)
- Added `llm_timeout` setting (default: 300 seconds / 5 minutes)
- Configurable via environment variable `LLM_TIMEOUT`

### 2. Improved Timeout Configuration (src/llm_adapter.py)
- Better timeout handling with separate connect/read/write timeouts
- Connect timeout: 10s (fast failure if Ollama is down)
- Read timeout: 300s (allows slow model processing)
- Write timeout: 30s
- Pool timeout: 10s

### 3. Better Error Messages
- Specific timeout error messages
- Suggestions for resolution (increase timeout, use faster model, check Ollama)

## Configuration

### Environment Variable
```bash
# In .env file
LLM_TIMEOUT=300  # 5 minutes (default)
```

### For Very Slow Systems
If you're still experiencing timeouts, increase further:
```bash
LLM_TIMEOUT=600  # 10 minutes
```

## Recommendations

### 1. Use GPU if Available
If you have a GPU, Ollama will use it automatically and be much faster:
```bash
# Check if GPU is available
ollama show qwen2.5:7b
```

### 2. Use a Smaller/Faster Model
For faster ingestion, consider using a smaller model:
```bash
# In .env
LLM_MODEL=qwen2.5:3b  # Smaller, faster model
```

### 3. Monitor Ollama Performance
Check Ollama logs to see if it's processing requests:
```bash
# Check Ollama logs
# On Windows: Check Ollama service logs
# On Linux: journalctl -u ollama
```

## Testing

After applying the fix, test ingestion:

```powershell
# Run diagnostic
python scripts/diagnose_ingestion.py

# Test simple ingestion
python scripts/test_simple_ingest.py

# Test batch ingestion
python scripts/ingest_resumes.py --dir data/resumes --batch-size 1
```

## Expected Behavior

With the fix:
- ✅ Ingestion should complete successfully
- ✅ Timeout errors should be rare (only for very large/complex documents)
- ✅ Clear error messages if timeout still occurs
- ✅ Configurable timeout via environment variable

## Performance Notes

- **CPU-only systems**: Expect 2-5 minutes per resume
- **GPU systems**: Expect 10-30 seconds per resume
- **Batch processing**: Use smaller batch sizes (1-2) on slow systems

## Next Steps

1. ✅ Timeout increased to 300 seconds
2. ✅ Better error handling added
3. ⏳ Test with actual resume files
4. ⏳ Monitor performance and adjust timeout if needed


