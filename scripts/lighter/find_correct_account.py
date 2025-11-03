#!/usr/bin/env python3
"""
Find the correct account_index for your Lighter API keys.
Tries multiple account indexes and shows detailed results.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def find_account():
    """Find which account_index has your API key"""
    
    import lighter
    
    # Get keys (support both naming conventions)
    api_key_private = os.getenv("LIGHTER_PRIVATE_KEY") or os.getenv("LIGHTER_API_KEY_PRIVATE")
    api_key_public = os.getenv("LIGHTER_PUBLIC_KEY") or os.getenv("LIGHTER_API_KEY_PUBLIC")
    api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))
    
    if not api_key_private:
        print("❌ LIGHTER_PRIVATE_KEY not found in .env")
        sys.exit(1)
    
    BASE_URL = "https://mainnet.zklighter.elliot.ai"
    
    print("=" * 70)
    print("LIGHTER ACCOUNT INDEX FINDER")
    print("=" * 70)
    print()
    print(f"Looking for API Key Index: {api_key_index}")
    print(f"Public Key: {api_key_public[:40]}...")
    print()
    print("Testing account indexes...")
    print()
    
    found = False
    errors_by_account = {}
    
    # Try wider range
    for account_index in range(51):  # 0-50
        try:
            client = lighter.SignerClient(
                url=BASE_URL,
                private_key=api_key_private,
                account_index=account_index,
                api_key_index=api_key_index,
            )
            
            err = client.check_client()
            
            if not err:
                print(f"{'='*70}")
                print(f"✅ SUCCESS! Found your account!")
                print(f"{'='*70}")
                print()
                print(f"Account Index: {account_index}")
                print(f"API Key Index: {api_key_index}")
                print()
                print("Add these to .env:")
                print(f"LIGHTER_ACCOUNT_INDEX={account_index}")
                print(f"LIGHTER_API_KEY_INDEX={api_key_index}")
                print()
                
                # Get balance
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
                    print(f"⚠️  Could not fetch balance: {e}")
                
                await client.close()
                found = True
                return account_index
            else:
                err_msg = str(err).lower()
                if "api key not found" in err_msg:
                    errors_by_account[account_index] = "key_not_found"
                elif "private key does not match" in err_msg:
                    errors_by_account[account_index] = "key_mismatch"
                    print(f"   Account {account_index}: ⚠️  Key exists but private key doesn't match")
                elif "invalid account index" not in err_msg:
                    errors_by_account[account_index] = "other"
                    print(f"   Account {account_index}: {str(err)[:50]}...")
            
            await client.close()
            
        except Exception as e:
            err_str = str(e).lower()
            if "api key not found" not in err_str and "invalid account" not in err_str:
                errors_by_account[account_index] = "exception"
    
    if not found:
        print()
        print("=" * 70)
        print("❌ Account not found in range 0-50")
        print("=" * 70)
        print()
        print("NEXT STEPS:")
        print()
        print("1. Check Lighter UI (app.lighter.xyz)")
        print("   - Go to Settings → API Keys")
        print("   - Look for 'Account Index' or 'Account Number' next to your API key")
        print("   - This might be different from what you think")
        print()
        print("2. Verify API key is fully registered:")
        print("   - If you just created it, wait 1-2 minutes for propagation")
        print("   - Try clicking 'Refresh' next to the API key in the UI")
        print()
        print("3. Check if private key matches:")
        print("   - The private key in .env should match the one you downloaded")
        print("   - It should be 80 characters (hex format)")
        print()
        print("4. Account index might be higher:")
        print("   - If you have multiple accounts, try higher indexes")
        print("   - Or query by ETH address if you know it")
        
        key_mismatches = [acc for acc, err in errors_by_account.items() if err == "key_mismatch"]
        if key_mismatches:
            print()
            print(f"⚠️  Found {len(key_mismatches)} account(s) with API key index {api_key_index},")
            print("   but private key doesn't match:")
            for acc in key_mismatches:
                print(f"   - Account {acc}")
            print()
            print("   This suggests the private key in .env might be incorrect.")
    
    return None

if __name__ == "__main__":
    result = asyncio.run(find_account())
    sys.exit(0 if result is not None else 1)

