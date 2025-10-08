#!/usr/bin/env python3
"""
Setup Lighter API key - registers your API key with Lighter
This only needs to be run ONCE to register the API key you generated
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def setup_api_key():
    """Register API key with Lighter"""

    try:
        import lighter
        import eth_account
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Run: pip install lighter-sdk eth-account")
        sys.exit(1)

    # Get environment variables
    eth_private_key = os.getenv("ETH_PRIVATE_KEY")
    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE")
    api_key_public = os.getenv("LIGHTER_API_KEY_PUBLIC")
    account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "1"))
    api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "3"))

    # Check for main wallet key
    if not eth_private_key:
        print("=" * 60)
        print("❌ ETH_PRIVATE_KEY not found in .env")
        print("=" * 60)
        print()
        print("You need your main Lighter wallet private key to register API keys.")
        print()
        print("Steps:")
        print("1. Export your Lighter wallet private key")
        print("2. Add to .env: ETH_PRIVATE_KEY=your_key_here")
        print("3. Run this script again")
        print()
        print("⚠️  IMPORTANT: Remove ETH_PRIVATE_KEY from .env after setup!")
        print("   The bot only needs API_KEY_PRIVATE_KEY to run.")
        sys.exit(1)

    if not api_key_private or not api_key_public:
        print("❌ LIGHTER_API_KEY_PRIVATE or LIGHTER_API_KEY_PUBLIC not found")
        sys.exit(1)

    # Mask keys for display
    masked_eth = f"{eth_private_key[:8]}...{eth_private_key[-8:]}"
    masked_api = f"{api_key_private[:8]}...{api_key_private[-8:]}"

    print("=" * 60)
    print("LIGHTER API KEY SETUP")
    print("=" * 60)
    print()
    print(f"Main wallet key: {masked_eth}")
    print(f"API key (private): {masked_api}")
    print(f"API key (public): {api_key_public[:16]}...")
    print(f"Account index: {account_index}")
    print(f"API key index: {api_key_index}")
    print()

    BASE_URL = "https://mainnet.zklighter.elliot.ai"

    try:
        # Get Ethereum address
        eth_acc = eth_account.Account.from_key(eth_private_key)
        eth_address = eth_acc.address
        print(f"✅ Ethereum address: {eth_address}")

        # Check if account exists
        api_client = lighter.ApiClient(configuration=lighter.Configuration(host=BASE_URL))
        account_api = lighter.AccountApi(api_client)

        print(f"\n🔄 Looking up account...")
        try:
            response = await account_api.accounts_by_l1_address(l1_address=eth_address)
            print(f"✅ Found {len(response.sub_accounts)} sub-account(s)")

            if account_index >= len(response.sub_accounts):
                print(f"\n❌ Account index {account_index} not found")
                print(f"   Available indexes: {[a.index for a in response.sub_accounts]}")
                await api_client.close()
                sys.exit(1)

            # Use the requested account index
            actual_index = response.sub_accounts[account_index].index
            print(f"✅ Using account index: {actual_index}")

        except lighter.ApiException as e:
            if hasattr(e, 'data') and e.data.message == "account not found":
                print(f"\n❌ No account found for address {eth_address}")
                print("   Make sure you've logged into Lighter and created an account first")
                await api_client.close()
                sys.exit(1)
            else:
                raise

        # Create SignerClient with the API key
        print(f"\n🔄 Registering API key...")
        tx_client = lighter.SignerClient(
            url=BASE_URL,
            private_key=api_key_private,
            account_index=actual_index,
            api_key_index=api_key_index,
        )

        # Register the API key
        response, err = await tx_client.change_api_key(
            eth_private_key=eth_private_key,
            new_pubkey=api_key_public,
        )

        if err:
            print(f"❌ Failed to register API key: {err}")
            await tx_client.close()
            await api_client.close()
            sys.exit(1)

        print(f"✅ API key registered successfully!")

        # Wait for propagation
        print(f"\n⏳ Waiting for API key to propagate (10 seconds)...")
        await asyncio.sleep(10)

        # Verify it worked
        print(f"🔄 Verifying API key...")
        err = tx_client.check_client()
        if err:
            print(f"⚠️  Verification warning: {err}")
            print("   API key may need more time to propagate")
        else:
            print(f"✅ API key verified!")

        # Clean up
        await tx_client.close()
        await api_client.close()

        print("\n" + "=" * 60)
        print("✅ SETUP COMPLETE!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. ⚠️  REMOVE ETH_PRIVATE_KEY from .env file (no longer needed)")
        print("2. Run: python3 scripts/test_lighter_connection.py")
        print("3. Fund your sub-account if needed")
        print()
        print("Your .env should only have:")
        print("  LIGHTER_API_KEY_PRIVATE=...")
        print("  LIGHTER_API_KEY_PUBLIC=...")
        print("  LIGHTER_ACCOUNT_INDEX=1")
        print("  LIGHTER_API_KEY_INDEX=3")

        return True

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(setup_api_key())
    sys.exit(0 if success else 1)
