#!/usr/bin/env python3
"""
Find your actual Lighter account index
Tries account indexes 0-100 to find which one is valid
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def find_account():
    """Find valid account index by brute force"""

    import lighter

    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE")

    BASE_URL = "https://mainnet.zklighter.elliot.ai"

    print("==" * 30)
    print("FINDING YOUR LIGHTER ACCOUNT INDEX")
    print("==" * 30)
    print()

    # Try account indexes 0-100
    for account_index in range(101):
        # Use API key index 3 (where we registered)
        api_key_index = 3

        try:
            client = lighter.SignerClient(
                url=BASE_URL,
                private_key=api_key_private,
                account_index=account_index,
                api_key_index=api_key_index,
            )

            err = client.check_client()
            if not err:
                print(f"✅ FOUND! Account index: {account_index}")
                print()
                print("Update your .env:")
                print(f"LIGHTER_ACCOUNT_INDEX={account_index}")
                await client.close()
                return account_index

            await client.close()

        except Exception as e:
            # Only print progress every 10 indexes
            if account_index % 10 == 0:
                print(f"Tested indexes 0-{account_index}...")

    print()
    print("❌ No valid account index found in range 0-100")
    return None

if __name__ == "__main__":
    result = asyncio.run(find_account())
    sys.exit(0 if result is not None else 1)
