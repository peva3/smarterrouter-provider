#!/usr/bin/env python3
"""
Test API connectivity for livebench and bigcodebench.
"""

import asyncio
import aiohttp
from datasets import load_dataset

async def test_livebench():
    """Test LiveBench API connectivity."""
    urls = [
        "https://livebench.ai/api/leaderboard",
        "https://livebench.ai/leaderboard/data"
    ]
    
    for url in urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as resp:
                    print(f"LiveBench URL: {url}")
                    print(f"  Status: {resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"  Data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                        return True
                    else:
                        print(f"  Response text: {await resp.text()[:200]}")
        except Exception as e:
            print(f"  Error: {type(e).__name__}: {e}")
    
    return False

def test_bigcodebench():
    """Test BigCodeBench dataset loading."""
    datasets_to_try = [
        "bigcode/bigcodebench",
        "bigcode/bigcodebench-test", 
        "bigcode/bigcodebench-hard",
    ]
    
    for ds_name in datasets_to_try:
        try:
            print(f"Trying dataset: {ds_name}")
            ds = load_dataset(ds_name, split="test", trust_remote_code=True)
            print(f"  Success! Dataset size: {len(ds)}")
            print(f"  Columns: {ds.column_names}")
            # Show first few entries
            for i in range(min(3, len(ds))):
                item = ds[i]
                print(f"  Sample {i}: {item}")
            return True
        except Exception as e:
            print(f"  Error: {type(e).__name__}: {e}")
    
    return False

async def main():
    print("=== Testing API Connectivity ===\n")
    
    print("1. Testing LiveBench API...")
    livebench_ok = await test_livebench()
    print(f"LiveBench connectivity: {'OK' if livebench_ok else 'FAILED'}\n")
    
    print("2. Testing BigCodeBench dataset...")
    bigcodebench_ok = test_bigcodebench()
    print(f"BigCodeBench connectivity: {'OK' if bigcodebench_ok else 'FAILED'}\n")
    
    # Test HuggingFace generic connectivity
    print("3. Testing HuggingFace Hub connectivity...")
    try:
        from huggingface_hub import list_datasets
        datasets = list(list_datasets(search="bigcodebench", limit=2))
        print(f"  Found datasets: {[d.id for d in datasets]}")
        hf_ok = True
    except Exception as e:
        print(f"  Error: {e}")
        hf_ok = False
    
    print("\n=== Summary ===")
    print(f"LiveBench: {'✓' if livebench_ok else '✗'}")
    print(f"BigCodeBench: {'✓' if bigcodebench_ok else '✗'}")
    print(f"HuggingFace Hub: {'✓' if hf_ok else '✗'}")

if __name__ == "__main__":
    asyncio.run(main())