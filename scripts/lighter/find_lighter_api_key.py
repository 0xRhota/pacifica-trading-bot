#!/usr/bin/env python3
"""
Find which index your Lighter API key is registered on
Tests all possible indexes to find where your key lives
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def find_api_key():
    """Try different indexes to find where the API key is registered"""

    import lighter

    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE")
    account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "1"))

    BASE_URL = "https://mainnet.zklighter.elliot.ai"

    print("=" * 60)
    print("SEARCHING FOR LIGHTER API KEY")
    print("=" * 60)
    print(f"\nAccount index: {account_index}")
    print(f"API key: {api_key_private[:8]}...{api_key_private[-8:]}")
    print()

    # Try common indexes
    test_indexes = [0, 1, 2, 3, 4, 5]  # Desktop, Mobile, and custom

    for api_key_index in test_indexes:
        print(f"🔄 Testing API key index {api_key_index}...", end=" ")

        try:
            client = lighter.SignerClient(
                url=BASE_URL,
                private_key=api_key_private,
                account_index=account_index,
                api_key_index=api_key_index,
            )

            err = client.check_client()
            if err:
                print(f"❌ {err}")
            else:
                print(f"✅ FOUND!")
                print()
                print("=" * 60)
                print(f"✅ YOUR API KEY IS REGISTERED AT INDEX {api_key_index}")
                print("=" * 60)
                print()
                print("Update your .env file:")
                print(f"LIGHTER_API_KEY_INDEX={api_key_index}")
                await client.close()
                return api_key_index

            await client.close()

        except Exception as e:
            print(f"❌ Error: {e}")

    print()
    print("=" * 60)
    print("❌ API KEY NOT FOUND ON ANY INDEX")
    print("=" * 60)
    print()
    print("This means the API key hasn't been registered yet.")
    print("You'll need to register it through Lighter UI or with ETH key.")
    return None

if __name__ == "__main__":
    result = asyncio.run(find_api_key())
    sys.exit(0 if result is not None else 1)
