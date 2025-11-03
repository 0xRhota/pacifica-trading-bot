#!/usr/bin/env python3
"""
Simple test script for Account Index 2, API Key Index 2
Run this once the key has fully propagated
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def test():
    import lighter
    
    api_key_private = os.getenv("LIGHTER_PRIVATE_KEY") or os.getenv("LIGHTER_API_KEY_PRIVATE")
    account_index = 2
    api_key_index = 2
    BASE_URL = "https://mainnet.zklighter.elliot.ai"
    
    print(f"Testing Account Index {account_index}, API Key Index {api_key_index}...")
    print()
    
    try:
        client = lighter.SignerClient(
            url=BASE_URL,
            private_key=api_key_private,
            account_index=account_index,
            api_key_index=api_key_index,
        )
        
        err = client.check_client()
        
        if err:
            print(f"❌ Failed: {err}")
            return False
        
        print("✅ SUCCESS! Connection works!")
        print()
        print(f"Configuration:")
        print(f"  LIGHTER_ACCOUNT_INDEX={account_index}")
        print(f"  LIGHTER_API_KEY_INDEX={api_key_index}")
        
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
                    print(f"💰 Balance: ${balance:.2f}")
            
            await api_client.close()
        except Exception as e:
            print(f"⚠️  Could not get balance: {e}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test())
    sys.exit(0 if success else 1)

