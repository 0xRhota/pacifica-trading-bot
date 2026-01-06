#!/usr/bin/env python3
"""
Paradex authentication test with subkey - using SDK's ParadexSubkey class
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def test_auth():
    """Test Paradex authentication with subkey using SDK"""
    try:
        from paradex_py import ParadexSubkey

        private_key = os.getenv("PARADEX_PRIVATE_SUBKEY")
        # Main account L2 address (the subkey belongs to this account)
        main_account = os.getenv("PARADEX_ACCOUNT_ADDRESS")

        if not private_key:
            print("ERROR: PARADEX_PRIVATE_SUBKEY not set in .env")
            return False

        print(f"Subkey private key: {private_key[:10]}...{private_key[-6:]}")
        print(f"Main account (L2): {main_account}")

        print("\nInitializing ParadexSubkey...")

        paradex = ParadexSubkey(
            env='prod',  # Literal type, not enum
            l2_private_key=private_key,
            l2_address=main_account,
        )

        print("ParadexSubkey initialized!")
        print(f"Account: {paradex.account}")
        print(f"L2 Address: {hex(paradex.account.l2_address)}")

        # Fetch account info via API client
        print("\nFetching account summary...")
        account = paradex.api_client.fetch_account_summary()
        print(f"Account: {account}")

        # Get balances
        print("\nFetching balances...")
        balances = paradex.api_client.fetch_balances()
        print(f"Balances: {balances}")

        print("\n✅ AUTH SUCCESS!")

        # Get available markets
        print("\nFetching markets...")
        markets = paradex.api_client.fetch_markets()
        if markets:
            symbols = [m.get('symbol') for m in markets.get('results', [])[:5]]
            print(f"Available markets (first 5): {symbols}")

        # Get BTC-USD-PERP price
        print("\nFetching ETH-USD-PERP BBO...")
        bbo = paradex.api_client.fetch_bbo(market="ETH-USD-PERP")
        print(f"ETH BBO: {bbo}")

        # Place a tiny test order (0.001 ETH ~ $3)
        print("\n--- TEST ORDER ---")
        print("Placing small limit buy order: 0.001 ETH @ $3000 (won't fill)...")

        try:
            from paradex_py.common.order import Order, OrderType, OrderSide
            from decimal import Decimal

            order_obj = Order(
                market="ETH-USD-PERP",
                order_type=OrderType.Limit,
                order_side=OrderSide.Buy,
                size=Decimal("0.001"),
                limit_price=Decimal("3000"),  # Well below market - won't fill
                client_id="test_order_001",
            )

            result = paradex.api_client.submit_order(order_obj)
            print(f"Order placed: {result}")

            # Cancel it
            order_id = result.get('id')
            if order_id:
                print(f"\nCanceling order {order_id}...")
                cancel = paradex.api_client.cancel_order(order_id=order_id)
                print(f"Cancel result: {cancel}")
        except Exception as e:
            print(f"Order error: {e}")
            import traceback
            traceback.print_exc()

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_auth())
