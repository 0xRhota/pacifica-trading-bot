#!/usr/bin/env python3
"""
Diagnose Lighter setup - check what's configured and what's missing
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def diagnose():
    """Diagnose Lighter configuration"""
    
    print("=" * 60)
    print("LIGHTER SETUP DIAGNOSIS")
    print("=" * 60)
    print()
    
    # Check environment variables (support both naming conventions)
    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE") or os.getenv("LIGHTER_PRIVATE_KEY")
    api_key_public = os.getenv("LIGHTER_API_KEY_PUBLIC") or os.getenv("LIGHTER_PUBLIC_KEY")
    account_index = os.getenv("LIGHTER_ACCOUNT_INDEX")
    api_key_index = os.getenv("LIGHTER_API_KEY_INDEX", "2")
    
    print("Environment Variables:")
    print(f"  LIGHTER_API_KEY_PRIVATE: {'✅ Set' if api_key_private else '❌ Missing'}")
    print(f"  LIGHTER_API_KEY_PUBLIC: {'✅ Set' if api_key_public else '❌ Missing'}")
    print(f"  LIGHTER_ACCOUNT_INDEX: {'✅ Set (' + account_index + ')' if account_index else '❌ Missing'}")
    print(f"  LIGHTER_API_KEY_INDEX: ✅ Set ({api_key_index})")
    print()
    
    if not api_key_private or not api_key_public:
        print("❌ Missing required API keys. Add them to .env")
        return
    
    # Test SDK import
    try:
        import lighter
        print("✅ Lighter SDK imported successfully")
    except ImportError as e:
        print(f"❌ Lighter SDK not installed: {e}")
        print("\nInstall with: pip install git+https://github.com/elliottech/lighter-python.git")
        return
    
    BASE_URL = "https://mainnet.zklighter.elliot.ai"
    
    # If account_index is set, test it directly
    if account_index:
        print(f"\n🔄 Testing known account index: {account_index}")
        try:
            client = lighter.SignerClient(
                url=BASE_URL,
                private_key=api_key_private,
                account_index=int(account_index),
                api_key_index=int(api_key_index),
            )
            
            err = client.check_client()
            if not err:
                print("✅ Connection successful!")
                await client.close()
                return
            
            print(f"❌ Connection failed: {err}")
            await client.close()
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # If account_index not set or test failed, try to find it
    print("\n🔄 Searching for account index...")
    print("   Testing common indexes with API key index 2...")
    
    found = False
    for acc_idx in range(0, 20):  # Try first 20 account indexes
        try:
            client = lighter.SignerClient(
                url=BASE_URL,
                private_key=api_key_private,
                account_index=acc_idx,
                api_key_index=int(api_key_index),
            )
            
            err = client.check_client()
            if not err:
                print(f"\n✅ FOUND! Account index: {acc_idx}")
                print(f"\nAdd to .env:")
                print(f"LIGHTER_ACCOUNT_INDEX={acc_idx}")
                found = True
                await client.close()
                break
            
            await client.close()
        except Exception as e:
            continue
    
    if not found:
        print("\n❌ Could not find valid account index")
        print("\nPossible issues:")
        print("1. API keys not yet registered on-chain")
        print("   → Check Lighter UI (app.lighter.xyz) to verify keys are active")
        print("2. Wrong API key index")
        print("   → Verify in Lighter UI which index your key uses")
        print("3. Account index not in range 0-19")
        print("   → Check Lighter UI for your account number")
        print("\nAccording to docs: https://apidocs.lighter.xyz/docs/get-started-for-programmers-1")
        print("If you signed with MetaMask, the keys should be registered.")
        print("Double-check in the Lighter UI that the API key is showing as 'active' or 'registered'")

if __name__ == "__main__":
    asyncio.run(diagnose())

