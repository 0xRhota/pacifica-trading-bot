#!/usr/bin/env python3
"""Manually construct and send SOL buy order"""

import asyncio
import os
import time
from dotenv import load_dotenv

load_dotenv()

async def manual_buy():
    import lighter
    from lighter.transactions import CreateOrder

    # Initialize client
    client = lighter.SignerClient(
        url="https://mainnet.zklighter.elliot.ai",
        private_key=os.getenv("LIGHTER_API_KEY_PRIVATE"),
        account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX")),
        api_key_index=int(os.getenv("LIGHTER_API_KEY_INDEX")),
    )

    print("Creating SOL buy order manually...")

    try:
        # Sign the order (this creates and signs the transaction)
        # Note: IOC orders don't need expiry, but trying LIMIT to see if it works
        result = client.sign_create_order(
            market_index=2,  # SOL market_id
            client_order_index=int(time.time() * 1000) % 1000000,  # Unique ID
            base_amount=50,  # 0.050 SOL (50 with 3 decimals)
            price=250000,  # High price ($250) to ensure quick fill
            is_ask=False,  # BUY
            order_type=client.ORDER_TYPE_LIMIT,  # Try LIMIT instead of MARKET
            time_in_force=client.ORDER_TIME_IN_FORCE_POST_ONLY,  # POST_ONLY for maker
            reduce_only=False,
            trigger_price=0,
        )

        print(f"Sign result type: {type(result)}")
        print(f"Sign result: {result}")

        if result is None:
            print("❌ sign_create_order returned None!")
            return

        signed_tx, nonce = result
        print(f"Signed transaction (nonce {nonce}): {signed_tx.to_json() if signed_tx else 'None'}")

        # Send the signed transaction
        result = await client.send_tx(
            tx_type=client.TX_TYPE_CREATE_ORDER,
            tx_info=signed_tx.to_json()
        )

        print(f"\n✅ ORDER SENT!")
        print(f"Result: {result}")

        # Wait and check position
        await asyncio.sleep(3)

        api_client = lighter.ApiClient(configuration=lighter.Configuration(host="https://mainnet.zklighter.elliot.ai"))
        account_api = lighter.AccountApi(api_client)

        account = await account_api.account(
            by="index",
            value=str(os.getenv("LIGHTER_ACCOUNT_INDEX"))
        )

        if hasattr(account, 'accounts') and account.accounts:
            acc = account.accounts[0]
            print(f"\nBalance: ${float(acc.available_balance):.2f}")

            if hasattr(acc, 'positions'):
                sol_pos = [p for p in acc.positions if p.market_id == 2 and float(p.position) != 0]
                if sol_pos:
                    pos = sol_pos[0]
                    print(f"\n✅ SOL POSITION OPENED!")
                    print(f"   Size: {pos.position} SOL")
                    print(f"   Entry: ${pos.avg_entry_price}")
                    print(f"   Value: ${pos.position_value}")
                    print(f"   PnL: ${pos.unrealized_pnl}")
                else:
                    print("\n⚠️  No SOL position found yet")

        await api_client.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    await client.close()

asyncio.run(manual_buy())
