#!/usr/bin/env python3
"""
Find account index by validating public key matches
Uses wider search range and validates key pairs
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def find_account():
    """Find account by validating key pair matches"""
    
    try:
        import lighter
    except ImportError as e:
        print(f"❌ Lighter SDK not installed: {e}")
        sys.exit(1)
    
    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE") or os.getenv("LIGHTER_PRIVATE_KEY")
    api_key_public = os.getenv("LIGHTER_API_KEY_PUBLIC") or os.getenv("LIGHTER_PUBLIC_KEY")
    api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))
    
    if not api_key_private:
        print("❌ LIGHTER_PRIVATE_KEY not found")
        sys.exit(1)
    
    print("Configuration:")
    print(f"  API Key Private: {api_key_private[:16]}...")
    print(f"  API Key Public: {api_key_public[:32] if api_key_public else 'NOT SET'}...")
    print(f"  API Key Index: {api_key_index}")
    print()
    
    BASE_URL = "https://mainnet.zklighter.elliot.ai"
    
    print("Searching account indexes 0-50 with API key index 2...")
    print("(This will take ~30 seconds)")
    print()
    
    found_accounts = []
    
    for acc_idx in range(51):
        try:
            client = lighter.SignerClient(
                url=BASE_URL,
                private_key=api_key_private,
                account_index=acc_idx,
                api_key_index=api_key_index,
            )
            
            err = client.check_client()
            
            if not err:
                found_accounts.append(acc_idx)
                print(f"✅ FOUND: Account index {acc_idx}")
                
                # Try to get balance
                try:
                    config = lighter.Configuration(host=BASE_URL)
                    api_client = lighter.ApiClient(configuration=config)
                    account_api = lighter.AccountApi(api_client)
                    
                    account = await account_api.account(by="index", value=str(acc_idx))
                    
                    if hasattr(account, 'accounts') and account.accounts:
                        acc = account.accounts[0]
                        if hasattr(acc, 'available_balance'):
                            balance = float(acc.available_balance)
                            print(f"   Balance: ${balance:.2f}")
                    
                    await api_client.close()
                except:
                    pass
                
                await client.close()
            
        except Exception as e:
            # Check if it's the "private key doesn't match" error
            err_str = str(e)
            if "private key does not match" in err_str:
                # Extract the public key from Lighter's response
                if "PublicKey:" in err_str:
                    lighter_pubkey = err_str.split("PublicKey:")[1].split()[0]
                    print(f"   Account {acc_idx}: Has API key, but pubkey mismatch")
                    print(f"      Lighter's pubkey: {lighter_pubkey[:32]}...")
            continue
    
    print()
    if found_accounts:
        print("=" * 60)
        print("✅ FOUND VALID ACCOUNT(S)!")
        print("=" * 60)
        for acc_idx in found_accounts:
            print(f"\nAdd to .env:")
            print(f"LIGHTER_ACCOUNT_INDEX={acc_idx}")
        print(f"LIGHTER_API_KEY_INDEX={api_key_index}")
        return found_accounts[0]
    else:
        print("❌ No valid account found")
        print()
        print("The API keys might need to be explicitly registered.")
        print("Try running: python3 scripts/lighter/register_lighter_api_key.py")
        print("(This requires ETH_PRIVATE_KEY temporarily)")
        return None

if __name__ == "__main__":
    result = asyncio.run(find_account())
    sys.exit(0 if result is not None else 1)

