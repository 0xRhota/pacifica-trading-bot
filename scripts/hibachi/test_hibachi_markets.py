"""
Quick test to diagnose Hibachi market endpoint response
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_markets():
    api_key = os.getenv("HIBACHI_PUBLIC_KEY")

    # Test Data API market endpoint
    url = "https://data-api.hibachi.xyz/market/exchange-info"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    print(f"Testing: {url}")
    print(f"API Key: {api_key[:20]}...")

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            print(f"\nStatus: {resp.status}")
            print(f"Headers: {dict(resp.headers)}")

            text = await resp.text()
            print(f"\nRaw Response:\n{text[:500]}...")

            if resp.status == 200:
                try:
                    json_data = await resp.json()
                    print(f"\nJSON Response type: {type(json_data)}")
                    if isinstance(json_data, list):
                        print(f"List length: {len(json_data)}")
                        if json_data:
                            print(f"First item: {json_data[0]}")
                    elif isinstance(json_data, dict):
                        print(f"Dict keys: {json_data.keys()}")
                except Exception as e:
                    print(f"Error parsing JSON: {e}")

if __name__ == "__main__":
    asyncio.run(test_markets())
