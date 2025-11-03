#!/usr/bin/env python3
"""
Find Lighter account index using AccountApi methods (per official docs)
According to docs: https://apidocs.lighter.xyz/docs/get-started-for-programmers-1
"In case you do not know your ACCOUNT_INDEX, you can find it by querying the AccountApi"
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def find_account_via_api():
    """Find account using AccountApi methods from docs"""
    
    try:
        import lighter
    except ImportError as e:
        print(f"❌ Lighter SDK not installed: {e}")
        sys.exit(1)
    
    api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE") or os.getenv("LIGHTER_PRIVATE_KEY")
    api_key_public = os.getenv("LIGHTER_API_KEY_PUBLIC") or os.getenv("LIGHTER_PUBLIC_KEY")
    api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))
    
    if not api_key_private or not api_key_public:
        print("❌ API keys not found in .env")
        sys.exit(1)
    
    BASE_URL = "https://mainnet.zklighter.elliot.ai"
    
    print("=" * 60)
    print("FINDING ACCOUNT INDEX VIA AccountApi (Official Method)")
    print("=" * 60)
    print()
    print("According to Lighter docs:")
    print("'In case you do not know your ACCOUNT_INDEX, you can find it")
    print("by querying the AccountApi for the data about your account'")
    print()
    
    config = lighter.Configuration(host=BASE_URL)
    api_client = lighter.ApiClient(configuration=config)
    account_api = lighter.AccountApi(api_client)
    
    # Method 1: Try to get account info by API key
    # The docs mention querying AccountApi - let's try different approaches
    print("Method 1: Querying API keys for all accounts...")
    print("   (Using api_key_index=255 to get all API keys)")
    print()
    
    # Try account indexes 0-20 to query their API keys
    for acc_idx in range(21):
        try:
            # Query API keys for this account (255 = get all keys)
            apikeys_response = await account_api.apikeys(
                account_index=acc_idx,
                api_key_index=255
            )
            
            # Check if our API key exists in the response
            if hasattr(apikeys_response, 'api_keys') and apikeys_response.api_keys:
                for key_info in apikeys_response.api_keys:
                    if hasattr(key_info, 'public_key'):
                        stored_pubkey = key_info.public_key
                        # Compare with our public key (strip 0x if present)
                        our_pubkey_clean = api_key_public.replace('0x', '').lower()
                        stored_pubkey_clean = stored_pubkey.replace('0x', '').lower()
                        
                        if stored_pubkey_clean == our_pubkey_clean or stored_pubkey_clean.endswith(our_pubkey_clean[-16:]):
                            print(f"✅ FOUND! Account Index: {acc_idx}")
                            print(f"   API Key Index: {key_info.api_key_index if hasattr(key_info, 'api_key_index') else '?'}")
                            print()
                            print("Add to .env:")
                            print(f"LIGHTER_ACCOUNT_INDEX={acc_idx}")
                            print(f"LIGHTER_API_KEY_INDEX={api_key_index}")
                            print()
                            
                            # Verify with SignerClient
                            try:
                                client = lighter.SignerClient(
                                    url=BASE_URL,
                                    private_key=api_key_private,
                                    account_index=acc_idx,
                                    api_key_index=api_key_index,
                                )
                                err = client.check_client()
                                if not err:
                                    print("✅ SignerClient validation: PASSED")
                                else:
                                    print(f"⚠️  SignerClient validation: {err}")
                                await client.close()
                            except Exception as e:
                                print(f"⚠️  SignerClient test failed: {e}")
                            
                            await api_client.close()
                            return acc_idx
        except lighter.ApiException as e:
            # Account doesn't exist or no keys - continue
            if "account not found" not in str(e).lower() and "api key not found" not in str(e).lower():
                # Other error - might be valid account
                pass
        except Exception as e:
            # Skip errors, continue searching
            pass
    
    # Method 2: If we had ETH address, we could use accounts_by_l1_address
    # But that requires ETH_PRIVATE_KEY which user doesn't want to provide
    print()
    print("Method 2: Would need ETH address to use accounts_by_l1_address()")
    print("   (Requires ETH_PRIVATE_KEY to derive address)")
    print()
    
    await api_client.close()
    
    print("❌ Could not find account via AccountApi")
    print()
    print("Alternative: Check Lighter UI (app.lighter.xyz)")
    print("- Go to Settings/API Keys")
    print("- Find your API key (index 2)")
    print("- Note the Account Index shown there")
    
    return None

if __name__ == "__main__":
    result = asyncio.run(find_account_via_api())
    sys.exit(0 if result is not None else 1)

