import asyncio
import time
import timeit
from typing import List

# Mock environment setup to allow imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reranker import get_reranker_model
from src.llm_adapter import ollama_llm_func
from src.embedding import embedding_func

async def benchmark_reranker():
    print("\nBenchmarking Reranker...")
    query = "skilled react developer"
    docs = [f"This is a resume for a React developer with {i} years experience." for i in range(50)]
    
    start = time.perf_counter()
    model = get_reranker_model()
    # Force load
    model.rerank(query, ["test"], top_k=1)
    
    load_time = time.perf_counter() - start
    print(f"Model Load Time: {load_time:.4f}s")
    
    start = time.perf_counter()
    results = await model.arerank(query, docs, top_k=10)
    duration = time.perf_counter() - start
    
    print(f"Rerank 50 docs: {duration:.4f}s ({(duration/50)*1000:.2f}ms per doc)")
    return duration

async def benchmark_llm():
    print("\nBenchmarking LLM (Ollama)...")
    prompt = "Say hello."
    
    start = time.perf_counter()
    response = await ollama_llm_func(prompt)
    duration = time.perf_counter() - start
    
    print(f"LLM Simple Gen: {duration:.4f}s")
    print(f"Response: {response}")
    return duration

async def benchmark_embedding():
    print("\nBenchmarking Embedding...")
    docs = ["Test document for embedding generation." for _ in range(10)]
    
    start = time.perf_counter()
    # Assuming embedding_func returns numpy array
    embeddings = await embedding_func(docs)
    duration = time.perf_counter() - start
    
    print(f"Embed 10 docs: {duration:.4f}s ({(duration/10)*1000:.2f}ms per doc)")
    return duration

async def main():
    print("Starting System Benchmark...")
    
    # 1. Reranker
    await benchmark_reranker()
    
    # 2. LLM
    await benchmark_llm()
    
    # 3. Embedding
    await benchmark_embedding()

if __name__ == "__main__":
    asyncio.run(main())
