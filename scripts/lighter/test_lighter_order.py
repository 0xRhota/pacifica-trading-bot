#!/usr/bin/env python3
"""
Test placing a SMALL order on Lighter
Make sure your account is funded first!
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_order():
    """Test a very small market order"""

    try:
        import lighter

        api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE")
        account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX"))
        api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX"))

        BASE_URL = "https://mainnet.zklighter.elliot.ai"

        print("=" * 60)
        print("LIGHTER ORDER TEST")
        print("=" * 60)
        print()

        # Connect
        print("🔄 Connecting...")
        client = lighter.SignerClient(
            url=BASE_URL,
            private_key=api_key_private,
            account_index=account_index,
            api_key_index=api_key_index,
        )

        err = client.check_client()
        if err:
            print(f"❌ Connection failed: {err}")
            await client.close()
            return False

        print(f"✅ Connected to account #{account_index}")
        print()

        # Check available order books
        print("🔄 Checking available markets...")
        api_client = lighter.ApiClient(configuration=lighter.Configuration(host=BASE_URL))
        orderbook_api = lighter.OrderApi(api_client)

        # Get order books
        try:
            orderbooks = await orderbook_api.order_books(blockchain="LIGHTCHAIN_ZKSYNC_MAINNET")
            print(f"✅ Found {len(orderbooks.order_books) if hasattr(orderbooks, 'order_books') else 0} markets")

            if hasattr(orderbooks, 'order_books') and orderbooks.order_books:
                print("\nAvailable markets:")
                for ob in orderbooks.order_books[:10]:  # Show first 10
                    print(f"  - {ob.order_book_id if hasattr(ob, 'order_book_id') else ob}")
                print()

        except Exception as e:
            print(f"⚠️  Could not fetch order books: {e}")
            print("Continuing anyway...")
            print()

        # WARNING: Uncomment only after verifying account is funded!
        print("⚠️  ORDER PLACEMENT DISABLED")
        print()
        print("To enable trading:")
        print("1. Fund your Lighter account at https://app.lighter.xyz")
        print("2. Verify balance in UI")
        print("3. Uncomment the order code in this script")
        print("4. Choose market and size")
        print()

        # Example order (COMMENTED OUT FOR SAFETY):
        """
        print("🔄 Placing test market order...")

        # Very small test order
        result, err = await client.create_market_order(
            order_book_id="SOL-PERP",  # Change to actual market name
            size=1,  # Very small size - CHECK LIGHTER DOCS FOR MIN SIZE
            is_buy=True,
        )

        if err:
            print(f"❌ Order failed: {err}")
        else:
            print(f"✅ Order placed!")
            print(f"   Result: {result}")
        """

        await client.close()
        await api_client.close()

        print("=" * 60)
        print("✅ CONNECTION TEST PASSED")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_order())
