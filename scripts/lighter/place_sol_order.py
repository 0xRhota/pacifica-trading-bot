#!/usr/bin/env python3
"""Place SOL buy order - catching SDK bug"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def buy_sol():
    import lighter
    import time

    client = lighter.SignerClient(
        url="https://mainnet.zklighter.elliot.ai",
        private_key=os.getenv("LIGHTER_API_KEY_PRIVATE"),
        account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX")),
        api_key_index=int(os.getenv("LIGHTER_API_KEY_INDEX")),
    )

    print("Placing SOL buy order...")
    print("Market: SOL (market_id=2)")
    print("Size: 0.050 SOL (minimum size)")
    print("Type: Market order")
    print()

    order_id = int(time.time() * 1000) % 1000000

    try:
        # Try the create_order method - it will error but might still work
        result = await client.create_order(
            market_index=2,  # SOL market_id
            client_order_index=order_id,
            base_amount=50,  # 0.050 SOL in millis (50 = 0.050 with 3 decimals)
            price=0,  # Market order
            is_ask=False,  # BUY
            order_type=client.ORDER_TYPE_MARKET,
            time_in_force=client.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
        )
        print(f"Success! Result: {result}")
    except AttributeError as e:
        # SDK bug - but order might have gone through
        print(f"SDK error (expected): {e}")
        print("Checking if order was actually placed...")

        await asyncio.sleep(2)

        # Check active orders
        api_client = lighter.ApiClient(configuration=lighter.Configuration(host="https://mainnet.zklighter.elliot.ai"))
        order_api = lighter.OrderApi(api_client)

        try:
            orders = await order_api.active_orders_by_account(
                account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX"))
            )
            print(f"Active orders: {orders}")
        except Exception as e2:
            print(f"Could not fetch orders: {e2}")

        # Check account details which includes positions
        account_api = lighter.AccountApi(api_client)
        try:
            account = await account_api.account(
                by="index",
                value=str(os.getenv("LIGHTER_ACCOUNT_INDEX"))
            )

            print(f"\nAccount details: {account}")

            # Look for positions in the account object
            if hasattr(account, 'accounts') and account.accounts:
                acc = account.accounts[0]
                if hasattr(acc, 'positions'):
                    print("\nPositions:")
                    for pos in acc.positions:
                        print(f"  Market {pos.market_index if hasattr(pos, 'market_index') else '?'}: {pos}")

                    # Check for SOL position (market_id=2)
                    sol_pos = [p for p in acc.positions if hasattr(p, 'market_index') and p.market_index == 2]
                    if sol_pos and hasattr(sol_pos[0], 'size') and sol_pos[0].size != 0:
                        print("\n✅ SOL POSITION FOUND! Order executed despite SDK error")
                        print(f"   Size: {sol_pos[0].size}")
                    else:
                        print("\n❌ No SOL position found - order may have failed")

        except Exception as e3:
            print(f"Could not fetch account: {e3}")
            import traceback
            traceback.print_exc()

        await api_client.close()
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

    await client.close()
    print("\nCheck https://app.lighter.xyz to verify")

asyncio.run(buy_sol())
