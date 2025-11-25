#!/usr/bin/env python3
"""
Debug: Show exact Lighter API calls and responses
"""

import asyncio
import lighter
import os
import json
from dotenv import load_dotenv

load_dotenv()


async def debug_api_calls():
    """Show raw API calls and responses"""

    print("=" * 80)
    print("LIGHTER API DEBUG - Raw Calls and Responses")
    print("=" * 80)
    print()

    lighter_account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "341823"))

    print(f"Using account_index: {lighter_account_index}")
    print()

    # Initialize API client
    config = lighter.Configuration(host='https://mainnet.zklighter.elliot.ai')

    async with lighter.ApiClient(config) as api_client:
        account_api = lighter.AccountApi(api_client)

        print("-" * 80)
        print("API CALL: account(by='index', value='341823')")
        print("-" * 80)
        print()

        try:
            account = await account_api.account(
                by="index",
                value=str(lighter_account_index)
            )

            print("✅ Response received")
            print()
            print("RAW RESPONSE OBJECT:")
            print(f"Type: {type(account)}")
            print()

            if hasattr(account, 'accounts') and account.accounts:
                print(f"Number of accounts: {len(account.accounts)}")
                print()

                acc = account.accounts[0]

                print("ACCOUNT OBJECT ATTRIBUTES:")
                print(f"Type: {type(acc)}")
                print()

                # Show all attributes
                attrs = [attr for attr in dir(acc) if not attr.startswith('_')]
                print("All attributes:")
                for attr in attrs:
                    if attr not in ['dict', 'json', 'to_dict', 'to_json', 'to_str', 'from_dict', 'from_json', 'from_orm',
                                   'construct', 'copy', 'parse_file', 'parse_obj', 'parse_raw', 'schema', 'schema_json',
                                   'update_forward_refs', 'validate', 'model_config', 'model_fields', 'model_fields_set',
                                   'model_extra', 'model_computed_fields', 'model_construct', 'model_copy', 'model_dump',
                                   'model_dump_json', 'model_json_schema', 'model_parametrized_name', 'model_post_init',
                                   'model_rebuild', 'model_validate', 'model_validate_json', 'model_validate_strings']:
                        try:
                            value = getattr(acc, attr)
                            print(f"  {attr}: {value}")
                        except:
                            pass

                print()
                print("-" * 80)
                print("KEY FIELDS:")
                print("-" * 80)
                print(f"account_index: {getattr(acc, 'account_index', 'NOT FOUND')}")
                print(f"available_balance: {getattr(acc, 'available_balance', 'NOT FOUND')}")
                print(f"total_asset_value: {getattr(acc, 'total_asset_value', 'NOT FOUND')}")
                print(f"collateral: {getattr(acc, 'collateral', 'NOT FOUND')}")
                print(f"cross_asset_value: {getattr(acc, 'cross_asset_value', 'NOT FOUND')}")
                print()

                # Try to_dict if available
                if hasattr(acc, 'to_dict'):
                    print("-" * 80)
                    print("FULL ACCOUNT DATA (JSON):")
                    print("-" * 80)
                    account_dict = acc.to_dict()
                    print(json.dumps(account_dict, indent=2, default=str))

            else:
                print("❌ No accounts found in response")
                print(f"Response: {account}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(debug_api_calls())
