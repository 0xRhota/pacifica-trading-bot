#!/usr/bin/env python3
"""Quick test buy on Lighter"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def buy():
    import lighter

    client = lighter.SignerClient(
        url="https://mainnet.zklighter.elliot.ai",
        private_key=os.getenv("LIGHTER_API_KEY_PRIVATE"),
        account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX")),
        api_key_index=int(os.getenv("LIGHTER_API_KEY_INDEX")),
    )

    print("Placing buy order...")

    # Try using create_order directly
    import time
    order_id = int(time.time() * 1000) % 1000000

    try:
        # SDK has a bug - call the underlying transaction method directly
        from lighter.transactions import CreateOrder

        tx = CreateOrder(
            market_index=2,
            client_order_index=order_id,
            base_amount=1,
            price=0,
            is_ask=False,
            order_type=client.ORDER_TYPE_MARKET,
            time_in_force=client.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
        )

        result = await client.send_tx(tx)
        print(f"Result: {result}")
        print("✅ Order sent! Check Lighter UI at https://app.lighter.xyz")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    await client.close()

asyncio.run(buy())
