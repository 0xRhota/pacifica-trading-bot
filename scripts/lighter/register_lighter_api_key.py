#!/usr/bin/env python3
"""
Register Lighter API Key - ONE TIME SETUP
This reads ETH_PRIVATE_KEY from .env, registers your API key, then reminds you to delete it
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def register_api_key():
    """Register the API key you generated in Lighter UI"""

    print("=" * 60)
    print("LIGHTER API KEY REGISTRATION")
    print("=" * 60)
    print()

    # Import dependencies
    try:
        import lighter
        import eth_account
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        sys.exit(1)

    # Get all needed values
    eth_private_key = os.getenv("ETH_PRIVATE_KEY")
    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE")
    api_key_public = os.getenv("LIGHTER_API_KEY_PUBLIC")
    account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "1"))
    api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "3"))

    # Check for ETH key
    if not eth_private_key:
        print("❌ ETH_PRIVATE_KEY not found in .env")
        print()
        print("Steps:")
        print("1. Add this line to .env:")
        print("   ETH_PRIVATE_KEY=your_lighter_wallet_private_key")
        print("2. Run this script again")
        print("3. Delete ETH_PRIVATE_KEY from .env after setup")
        sys.exit(1)

    if not api_key_private or not api_key_public:
        print("❌ LIGHTER_API_KEY_PRIVATE or LIGHTER_API_KEY_PUBLIC not found")
        sys.exit(1)

    # Show what we're working with (masked)
    print("Configuration:")
    print(f"  ETH key: {eth_private_key[:6]}...{eth_private_key[-4:]}")
    print(f"  API key (private): {api_key_private[:8]}...{api_key_private[-8:]}")
    print(f"  API key (public): {api_key_public[:16]}...")
    print(f"  Account index: {account_index}")
    print(f"  API key index: {api_key_index}")
    print()

    BASE_URL = "https://mainnet.zklighter.elliot.ai"

    try:
        # Get Ethereum address
        eth_acc = eth_account.Account.from_key(eth_private_key)
        eth_address = eth_acc.address
        print(f"✅ Ethereum address: {eth_address}")
        print()

        # Initialize API client
        api_client = lighter.ApiClient(configuration=lighter.Configuration(host=BASE_URL))
        account_api = lighter.AccountApi(api_client)

        # Look up account
        print("🔄 Looking up Lighter account...")
        try:
            response = await account_api.accounts_by_l1_address(l1_address=eth_address)

            if len(response.sub_accounts) == 0:
                print("❌ No accounts found for this address")
                print("   Make sure you've logged into Lighter and created an account")
                await api_client.close()
                sys.exit(1)

            print(f"✅ Found {len(response.sub_accounts)} sub-account(s)")
            for i, acc in enumerate(response.sub_accounts):
                print(f"   - Index {i}: Account #{acc.index}")
            print()

            # Verify the account index exists
            if account_index >= len(response.sub_accounts):
                print(f"❌ Account index {account_index} not found")
                print(f"   Available indexes: 0 to {len(response.sub_accounts) - 1}")
                await api_client.close()
                sys.exit(1)

            actual_account_index = response.sub_accounts[account_index].index
            print(f"✅ Using account index {account_index} (Account #{actual_account_index})")
            print()

        except lighter.ApiException as e:
            error_msg = e.data.message if hasattr(e, 'data') else str(e)
            print(f"❌ API error: {error_msg}")
            await api_client.close()
            sys.exit(1)

        # Initialize signer client with the API key
        print("🔄 Initializing SignerClient...")
        tx_client = lighter.SignerClient(
            url=BASE_URL,
            private_key=api_key_private,
            account_index=actual_account_index,
            api_key_index=api_key_index,
        )
        print("✅ SignerClient created")
        print()

        # Register the API key (this signs a message with ETH key)
        print("🔄 Registering API key...")
        print("   (Signing message locally with your ETH key)")
        print()

        response, err = await tx_client.change_api_key(
            eth_private_key=eth_private_key,
            new_pubkey=api_key_public,
        )

        if err:
            print(f"❌ Registration failed: {err}")
            await tx_client.close()
            await api_client.close()
            sys.exit(1)

        print("✅ API key registered successfully!")
        print()

        # Wait for propagation
        print("⏳ Waiting 10 seconds for API key to propagate...")
        await asyncio.sleep(10)

        # Verify registration
        print("🔄 Verifying registration...")
        err = tx_client.check_client()

        if err:
            print(f"⚠️  Verification returned: {err}")
            print("   API key may need more time to propagate")
            print("   Try running test_lighter_connection.py in a few minutes")
        else:
            print("✅ API key verified and working!")

        # Clean up
        await tx_client.close()
        await api_client.close()

        # Success message
        print()
        print("=" * 60)
        print("✅ REGISTRATION COMPLETE!")
        print("=" * 60)
        print()
        print("⚠️  IMPORTANT - DO THIS NOW:")
        print("=" * 60)
        print("1. Open .env file")
        print("2. DELETE this line:")
        print("   ETH_PRIVATE_KEY=...")
        print("3. Save .env")
        print()
        print("The bot only needs these keys going forward:")
        print("  ✅ LIGHTER_API_KEY_PRIVATE")
        print("  ✅ LIGHTER_API_KEY_PUBLIC")
        print("  ✅ LIGHTER_ACCOUNT_INDEX")
        print("  ✅ LIGHTER_API_KEY_INDEX")
        print()
        print("After deleting ETH_PRIVATE_KEY, test with:")
        print("  python3 scripts/test_lighter_connection.py")
        print("=" * 60)

        return True

    except Exception as e:
        print()
        print(f"❌ Registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(register_api_key())
    sys.exit(0 if success else 1)
