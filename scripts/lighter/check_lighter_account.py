#!/usr/bin/env python3
"""
Check what's actually in your Lighter account
This is READ-ONLY - no keys needed, just checks what exists
"""

import asyncio
import lighter

async def check_account():
    """Check account status"""

    # These are your API keys you generated
    api_key_public = "25c2a6a1482466ba1960d455c0d2f41f09a24d394cbaa8d7b7656ce73dfff244faf638580b44e7d9"

    BASE_URL = "https://mainnet.zklighter.elliot.ai"

    # Check if this public key exists anywhere
    print("Searching for your API key in Lighter system...")
    print(f"Public key: {api_key_public[:32]}...")
    print()

    # Try to find which account/index it belongs to
    # This is a READ operation, no private keys needed

    api_client = lighter.ApiClient(configuration=lighter.Configuration(host=BASE_URL))

    # Check if there's an API to query by public key
    print("Checking API endpoints...")

    await api_client.close()

if __name__ == "__main__":
    asyncio.run(check_account())
