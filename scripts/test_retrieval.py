"""
Retrieval mode testing script.
Tests all LightRAG retrieval modes and validates fallback mechanisms.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_mode(rag, mode: str, query: str):
    """Test a single retrieval mode."""
    from lightrag import QueryParam
    
    print(f"\n🔍 Testing mode: {mode}")
    print("-" * 40)
    
    start = time.time()
    
    try:
        response = await rag.aquery(query, param=QueryParam(mode=mode))
        elapsed = time.time() - start
        
        if response:
            preview = response[:200] + "..." if len(response) > 200 else response
            print(f"✅ Success ({elapsed:.2f}s)")
            print(f"📝 Response preview:\n{preview}")
            return True, elapsed
        else:
            print(f"⚠️ Empty response ({elapsed:.2f}s)")
            return False, elapsed
            
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Failed ({elapsed:.2f}s): {e}")
        return False, elapsed


async def test_dual_retrieval(rag, query: str):
    """Test custom dual-level retrieval with fallback."""
    from src.dual_retrieval import DualLevelRetrieval
    
    print("\n🔍 Testing Dual-Level Retrieval with Fallback")
    print("-" * 40)
    
    start = time.time()
    
    try:
        retrieval = DualLevelRetrieval(rag)
        result = await retrieval.query_with_fallback(query, preferred_mode="mix")
        elapsed = time.time() - start
        
        preview = result.response[:200] + "..." if len(result.response) > 200 else result.response
        
        print(f"✅ Success ({elapsed:.2f}s)")
        print(f"📊 Mode used: {result.mode_used}")
        print(f"🔄 Fallback used: {result.fallback_used}")
        print(f"📝 Response preview:\n{preview}")
        
        return True, elapsed
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Failed ({elapsed:.2f}s): {e}")
        return False, elapsed


async def main():
    """Run all retrieval tests."""
    from src.rag_config import get_rag_manager
    
    print("\n" + "="*50)
    print("🧪 LightRAG ATS - Retrieval Mode Testing")
    print("="*50)
    
    # Test query
    test_query = "Find Python developers with 5 years of experience"
    print(f"\n📌 Test query: {test_query}")
    
    # Initialize RAG
    print("\n🔧 Initializing RAG system...")
    try:
        manager = get_rag_manager()
        rag = await manager.initialize()
        print("✅ RAG initialized")
    except Exception as e:
        print(f"❌ RAG initialization failed: {e}")
        return False
    
    # Test each mode
    modes = ["naive", "local", "global", "hybrid", "mix"]
    results = {}
    
    for mode in modes:
        success, elapsed = await test_mode(rag, mode, test_query)
        results[mode] = {"success": success, "time": elapsed}
    
    # Test dual retrieval with fallback
    success, elapsed = await test_dual_retrieval(rag, test_query)
    results["dual_retrieval"] = {"success": success, "time": elapsed}
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary")
    print("="*50)
    
    for mode, result in results.items():
        icon = "✅" if result["success"] else "❌"
        print(f"  {icon} {mode}: {result['time']:.2f}s")
    
    successful = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    print(f"\n📈 Passed: {successful}/{total}")
    
    # Performance recommendations
    if results.get("mix", {}).get("success"):
        print("\n💡 Recommendation: Use 'mix' mode for best results")
    elif results.get("hybrid", {}).get("success"):
        print("\n💡 Recommendation: Use 'hybrid' mode (mix unavailable)")
    elif results.get("naive", {}).get("success"):
        print("\n💡 Recommendation: Use 'naive' mode (advanced modes unavailable)")
    
    return successful > 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
