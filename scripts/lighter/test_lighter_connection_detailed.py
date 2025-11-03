#!/usr/bin/env python3
"""
Test Lighter connection with detailed error reporting
Shows exactly what's happening and why connection might fail
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def test_connection():
    """Test connection with detailed diagnostics"""
    
    print("=" * 60)
    print("LIGHTER CONNECTION TEST (DETAILED)")
    print("=" * 60)
    print()
    
    # Import
    try:
        import lighter
    except ImportError as e:
        print(f"❌ Lighter SDK not installed: {e}")
        sys.exit(1)
    
    # Get credentials
    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE") or os.getenv("LIGHTER_PRIVATE_KEY")
    api_key_public = os.getenv("LIGHTER_API_KEY_PUBLIC") or os.getenv("LIGHTER_PUBLIC_KEY")
    account_index = os.getenv("LIGHTER_ACCOUNT_INDEX")
    api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))
    
    if not api_key_private:
        print("❌ API key private not found")
        sys.exit(1)
    
    BASE_URL = "https://mainnet.zklighter.elliot.ai"
    
    # Try account indexes 0-10
    print(f"Testing with API key index: {api_key_index}")
    print(f"Testing account indexes 0-10...")
    print()
    
    for acc_idx in range(11):
        try:
            print(f"Testing account index {acc_idx}...", end=" ")
            
            client = lighter.SignerClient(
                url=BASE_URL,
                private_key=api_key_private,
                account_index=acc_idx,
                api_key_index=api_key_index,
            )
            
            # Try check_client
            err = client.check_client()
            
            if err:
                print(f"❌ Error: {err}")
                await client.close()
                continue
            
            print("✅ SUCCESS!")
            print()
            print("=" * 60)
            print("✅ CONNECTION WORKING!")
            print("=" * 60)
            print()
            print(f"Valid configuration:")
            print(f"  Account Index: {acc_idx}")
            print(f"  API Key Index: {api_key_index}")
            print()
            print("Add to .env:")
            print(f"LIGHTER_ACCOUNT_INDEX={acc_idx}")
            print(f"LIGHTER_API_KEY_INDEX={api_key_index}")
            print()
            
            # Try to get balance to verify
            try:
                config = lighter.Configuration(host=BASE_URL)
                api_client = lighter.ApiClient(configuration=config)
                account_api = lighter.AccountApi(api_client)
                
                account = await account_api.account(
                    by="index",
                    value=str(acc_idx)
                )
                
                if hasattr(account, 'accounts') and account.accounts:
                    acc = account.accounts[0]
                    if hasattr(acc, 'available_balance'):
                        balance = float(acc.available_balance)
                        print(f"💰 Account Balance: ${balance:.2f}")
                
                await api_client.close()
            except Exception as e:
                print(f"⚠️  Could not fetch balance: {e}")
            
            await client.close()
            return True
            
        except Exception as e:
            print(f"❌ Exception: {type(e).__name__}: {e}")
            continue
    
    print()
    print("❌ No valid account index found")
    print()
    print("Next steps:")
    print("1. Verify in Lighter UI (app.lighter.xyz) that your API key is registered")
    print("2. Check if there's a specific account number shown in the UI")
    print("3. The account index might be higher than 10")
    print()
    print("According to Lighter docs, if you signed with MetaMask when creating")
    print("the API key, it should be registered. But you may need to verify it's")
    print("showing as 'active' in the Lighter UI.")
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)

