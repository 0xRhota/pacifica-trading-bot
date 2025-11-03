#!/usr/bin/env python3
"""
Test Lighter DEX connection
Verifies API keys work and can connect to Lighter mainnet
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_lighter_connection():
    """Test connection to Lighter DEX"""

    # Import Lighter SDK
    try:
        import lighter
        print("✅ Lighter SDK imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Lighter SDK: {e}")
        sys.exit(1)

    # Get credentials from environment (support both naming conventions)
    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE") or os.getenv("LIGHTER_PRIVATE_KEY")
    account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "1"))
    api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))

    if not api_key_private:
        print("❌ LIGHTER_API_KEY_PRIVATE not found in .env")
        sys.exit(1)

    # Mask key for display (show first 8 and last 8 chars)
    masked_key = f"{api_key_private[:8]}...{api_key_private[-8:]}"
    print(f"✅ Found API key: {masked_key}")
    print(f"✅ Account index: {account_index}")
    print(f"✅ API key index: {api_key_index}")

    # Test connection
    print("\n🔄 Testing connection to Lighter mainnet...")

    try:
        # Initialize client
        BASE_URL = "https://mainnet.zklighter.elliot.ai"

        client = lighter.SignerClient(
            url=BASE_URL,
            private_key=api_key_private,
            account_index=account_index,
            api_key_index=api_key_index,
        )

        print(f"✅ SignerClient initialized")
        print(f"   URL: {BASE_URL}")

        # Verify client is valid
        err = client.check_client()
        if err:
            print(f"❌ Client check failed: {err}")
            await client.close()
            sys.exit(1)

        print("✅ Client validated successfully")

        # Clean up
        await client.close()

        print("\n" + "=" * 60)
        print("✅ LIGHTER CONNECTION TEST PASSED")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Fund your sub-account with trading capital")
        print("2. Test order placement on testnet first")
        print("3. Integrate with multi-DEX bot")

        return True

    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("LIGHTER DEX CONNECTION TEST")
    print("=" * 60)
    print()

    success = asyncio.run(test_lighter_connection())
    sys.exit(0 if success else 1)
