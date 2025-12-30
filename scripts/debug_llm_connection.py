import asyncio
from src.llm_adapter import get_ollama_adapter

async def check_connection():
    adapter = get_ollama_adapter()
    print(f"Testing connection to: {adapter.base_url}")
    print(f"Using model: {adapter.model}")
    
    try:
        # Simple health check ping
        is_healthy = await adapter.check_health()
        print(f"Health Check: {'✅ PASSED' if is_healthy else '❌ FAILED'}")
        
        if is_healthy:
            # Simple generation test
            print("Attempting simple generation...")
            response = await adapter.generate("Hello, are you there?", max_tokens=10)
            print(f"Response: {response}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(check_connection())
