#!/usr/bin/env python3
"""
Find the actual account index from your ETH address
This helps debug the account_index vs sub_accounts array confusion
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def get_account_index():
    """Get the actual account index"""

    import lighter
    import eth_account

    # We need the ETH key temporarily to check account
    eth_private_key = os.getenv("ETH_PRIVATE_KEY")

    if not eth_private_key:
        print("ERROR: Please temporarily add ETH_PRIVATE_KEY back to .env")
        print("We need it to look up your account info")
        print("(Delete it again after this runs)")
        sys.exit(1)

    BASE_URL = "https://mainnet.zklighter.elliot.ai"

    # Get Ethereum address
    eth_acc = eth_account.Account.from_key(eth_private_key)
    eth_address = eth_acc.address
    print(f"ETH address: {eth_address}")
    print()

    # Initialize API client
    api_client = lighter.ApiClient(configuration=lighter.Configuration(host=BASE_URL))
    account_api = lighter.AccountApi(api_client)

    # Look up account
    print("Looking up Lighter account...")
    try:
        response = await account_api.accounts_by_l1_address(l1_address=eth_address)

        if len(response.sub_accounts) == 0:
            print("No accounts found")
            await api_client.close()
            sys.exit(1)

        print(f"Found {len(response.sub_accounts)} sub-account(s):")
        for i, acc in enumerate(response.sub_accounts):
            print(f"  Array index {i}: Account index {acc.index}")
        print()

        print("The ACTUAL account index you should use is:", response.sub_accounts[0].index)
        print()
        print("Update your .env:")
        print(f"LIGHTER_ACCOUNT_INDEX={response.sub_accounts[0].index}")

        await api_client.close()

    except Exception as e:
        print(f"Error: {e}")
        await api_client.close()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(get_account_index())
