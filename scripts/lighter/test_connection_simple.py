#!/usr/bin/env python3
"""
Simple Lighter connection test using just API keys
Tests the exact flow from the docs
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def test():
    """Test connection per Lighter docs"""
    
    import lighter
    
    # Get API keys (support both naming conventions)
    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE") or os.getenv("LIGHTER_PRIVATE_KEY")
    api_key_public = os.getenv("LIGHTER_API_KEY_PUBLIC") or os.getenv("LIGHTER_PUBLIC_KEY")
    api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))
    
    if not api_key_private:
        print("❌ LIGHTER_PRIVATE_KEY not found in .env")
        sys.exit(1)
    
    BASE_URL = "https://mainnet.zklighter.elliot.ai"
    
    print("=" * 60)
    print("LIGHTER CONNECTION TEST (Per Official Docs)")
    print("=" * 60)
    print()
    print("According to docs:")
    print("- SignerClient only needs API_KEY_PRIVATE_KEY (after registration)")
    print("- Initialize with: account_index, api_key_index")
    print()
    
    # Try common account indexes
    # According to docs, if you don't know it, query AccountApi
    # But that requires ETH address or brute force
    
    print(f"Testing account indexes 0-10 with API key index {api_key_index}...")
    print()
    
    found = False
    
    for account_index in range(11):
        try:
            # Per docs: Initialize SignerClient
            client = lighter.SignerClient(
                url=BASE_URL,
                private_key=api_key_private,
                account_index=account_index,
                api_key_index=api_key_index,
            )
            
            # Check if client is valid (per docs, check_client validates)
            err = client.check_client()
            
            if not err:
                print(f"✅ SUCCESS! Account Index: {account_index}")
                print()
                print("Configuration:")
                print(f"  Account Index: {account_index}")
                print(f"  API Key Index: {api_key_index}")
                print()
                print("Add to .env:")
                print(f"LIGHTER_ACCOUNT_INDEX={account_index}")
                print()
                
                # Test getting account info
                try:
                    config = lighter.Configuration(host=BASE_URL)
                    api_client = lighter.ApiClient(configuration=config)
                    account_api = lighter.AccountApi(api_client)
                    
                    account = await account_api.account(by="index", value=str(account_index))
                    
                    if hasattr(account, 'accounts') and account.accounts:
                        acc = account.accounts[0]
                        if hasattr(acc, 'available_balance'):
                            balance = float(acc.available_balance)
                            print(f"💰 Account Balance: ${balance:.2f}")
                    
                    await api_client.close()
                except Exception as e:
                    print(f"⚠️  Could not fetch account details: {e}")
                
                await client.close()
                found = True
                return True
            
            await client.close()
            
        except Exception as e:
            err_msg = str(e)
            # Only show meaningful errors
            if "api key not found" in err_msg.lower():
                pass  # Expected - key not on this account
            elif "private key does not match" in err_msg.lower():
                # Key exists but doesn't match - wrong key pair
                print(f"   Account {account_index}: Has API key but private key mismatch")
            elif "invalid account index" not in err_msg.lower():
                print(f"   Account {account_index}: {err_msg[:60]}...")
            continue
    
    if not found:
        print("❌ No valid account found in range 0-10")
        print()
        print("According to Lighter docs:")
        print("If you don't know ACCOUNT_INDEX, query AccountApi")
        print("But that requires ETH address from accounts_by_l1_address()")
        print()
        print("Quick fix: Check Lighter UI (app.lighter.xyz)")
        print("- Go to Settings → API Keys")
        print("- Your API key (index 2) should show the Account Index")
        print("- Add that number to .env as LIGHTER_ACCOUNT_INDEX")
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)

