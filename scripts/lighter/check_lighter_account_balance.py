#!/usr/bin/env python3
"""
Check Lighter account balance and available markets
Run this before placing any orders
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def check_account():
    """Check account status and balance"""

    try:
        import lighter

        api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE")
        account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX"))
        api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX"))

        BASE_URL = "https://mainnet.zklighter.elliot.ai"

        print("=" * 60)
        print("LIGHTER ACCOUNT CHECK")
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
            return False

        print(f"✅ Connected to account #{account_index}")
        print()

        # Initialize API client for read-only queries
        api_client = lighter.ApiClient(configuration=lighter.Configuration(host=BASE_URL))

        # Try to get order books to see available markets
        print("🔄 Fetching available markets...")
        orderbook_api = lighter.OrderBookApi(api_client)

        # Common perpetual markets on Lighter
        test_symbols = ["BTCPERP", "ETHPERP", "SOLPERP", "BTC-PERP", "ETH-PERP", "SOL-PERP"]

        available_markets = []
        for symbol in test_symbols:
            try:
                # Try to get orderbook for this symbol
                orderbook = await orderbook_api.orderbook(blockchain="LIGHTCHAIN_ZKSYNC_MAINNET", order_book_id=symbol)
                available_markets.append(symbol)
                print(f"  ✅ {symbol}")
            except Exception:
                pass

        if available_markets:
            print()
            print(f"✅ Found {len(available_markets)} markets:")
            for market in available_markets:
                print(f"   - {market}")
        else:
            print("  ℹ️  Unable to auto-detect markets via API")
            print("  Check https://app.lighter.xyz for available markets")

        print()
        print("=" * 60)
        print("ACCOUNT FUNDING CHECK")
        print("=" * 60)
        print()
        print("⚠️  Before trading, ensure your account is funded:")
        print("1. Go to https://app.lighter.xyz")
        print(f"2. Connect wallet and switch to account #{account_index}")
        print("3. Deposit USDC or other collateral")
        print("4. Verify balance shows in UI")
        print()
        print("💡 Recommended first trade:")
        print("   - Market: SOL-PERP or BTC-PERP")
        print("   - Size: $5-10 USD equivalent")
        print("   - Type: Market order")
        print()

        await client.close()
        await api_client.close()

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(check_account())
