#!/usr/bin/env python3
"""
Discover Lighter Account Index and API Key Index from API keys only
Uses brute force approach - tries common indexes to find valid configuration
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def discover_config():
    """Discover account_index and api_key_index by testing combinations"""
    
    print("=" * 60)
    print("LIGHTER CONFIGURATION DISCOVERY")
    print("=" * 60)
    print()
    
    # Import Lighter SDK
    try:
        import lighter
        print("✅ Lighter SDK imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Lighter SDK: {e}")
        print("\nInstall with: pip install git+https://github.com/elliottech/lighter-python.git")
        sys.exit(1)
    
    # Get API keys from env (support both naming conventions)
    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE") or os.getenv("LIGHTER_PRIVATE_KEY")
    api_key_public = os.getenv("LIGHTER_API_KEY_PUBLIC") or os.getenv("LIGHTER_PUBLIC_KEY")
    
    if not api_key_private:
        print("❌ LIGHTER_API_KEY_PRIVATE not found in .env")
        sys.exit(1)
    
    if not api_key_public:
        print("❌ LIGHTER_API_KEY_PUBLIC not found in .env")
        sys.exit(1)
    
    print(f"✅ API keys found")
    print(f"   Private: {api_key_private[:8]}...{api_key_private[-8:]}")
    print(f"   Public: {api_key_public[:16]}...")
    print()
    
    BASE_URL = "https://mainnet.zklighter.elliot.ai"
    
    # Try common combinations
    # Account index: Usually 0 (main) or higher for sub-accounts
    # API key index: Usually 2-254 (0=Desktop, 1=Mobile, 2+ are API keys)
    
    print("🔍 Searching for valid configuration...")
    print("   (This may take a minute)")
    print()
    
    found = False
    
    # Try API key indexes 2-10 first (most common)
    for api_key_index in range(2, 11):
        # Try account indexes 0-10
        for account_index in range(11):
            try:
                client = lighter.SignerClient(
                    url=BASE_URL,
                    private_key=api_key_private,
                    account_index=account_index,
                    api_key_index=api_key_index,
                )
                
                # Test if this combination works
                err = client.check_client()
                if not err:
                    print("=" * 60)
                    print("✅ FOUND VALID CONFIGURATION!")
                    print("=" * 60)
                    print()
                    print(f"Account Index: {account_index}")
                    print(f"API Key Index: {api_key_index}")
                    print()
                    print("Add these to your .env file:")
                    print(f"LIGHTER_ACCOUNT_INDEX={account_index}")
                    print(f"LIGHTER_API_KEY_INDEX={api_key_index}")
                    print()
                    
                    # Try to get account info to verify
                    try:
                        config = lighter.Configuration(host=BASE_URL)
                        api_client = lighter.ApiClient(configuration=config)
                        account_api = lighter.AccountApi(api_client)
                        
                        account = await account_api.account(
                            by="index",
                            value=str(account_index)
                        )
                        
                        if hasattr(account, 'accounts') and account.accounts:
                            acc = account.accounts[0]
                            if hasattr(acc, 'available_balance'):
                                balance = float(acc.available_balance)
                                print(f"✅ Verified: Account balance: ${balance:.2f}")
                        
                        await api_client.close()
                    except Exception as e:
                        print(f"⚠️  Could not verify account details: {e}")
                    
                    await client.close()
                    found = True
                    return (account_index, api_key_index)
                
                await client.close()
                
            except Exception as e:
                # Expected failures - continue searching
                continue
    
    if not found:
        print("❌ Could not find valid configuration")
        print()
        print("This could mean:")
        print("1. API keys not yet registered on-chain")
        print("2. Account index is higher than 10")
        print("3. API key index is higher than 10")
        print()
        print("Try:")
        print("- Check Lighter UI (app.lighter.xyz) for Account Index and API Key Index")
        print("- Or register keys via: python3 scripts/lighter/register_lighter_api_key.py")
        return None
    
    return None

if __name__ == "__main__":
    result = asyncio.run(discover_config())
    sys.exit(0 if result else 1)

