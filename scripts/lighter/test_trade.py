#!/usr/bin/env python3
"""
LIGHTER TRADE TEST
Place a small test order on Lighter to verify everything works

BEFORE RUNNING:
1. Fund your Lighter account at https://app.lighter.xyz
2. Verify you have balance (USDC or other collateral)
3. Set the market and size below
"""

import asyncio
import os
from dotenv import load_dotenv
from utils.dex_logger import MultiDEXLogger

load_dotenv()

# Initialize secure logger
logger = MultiDEXLogger()
lighter_log = logger.lighter

# ============================================================
# CONFIGURATION - EDIT THESE
# ============================================================

MARKET_INDEX = 2  # 2 = SOL-PERP (matching your Pacifica trades)
# Common indexes:
# 0 = BTC-PERP
# 1 = ETH-PERP
# 2 = SOL-PERP

TEST_SIZE = 1  # TINY size for first test (1 unit)
# This is integer units - exact conversion depends on market
# Starting VERY SMALL to test!

IS_BUY = True  # True for long, False for short

# ============================================================

async def test_trade():
    """Place a test trade on Lighter"""

    try:
        import lighter

        # Load credentials
        api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE")
        account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX"))
        api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX"))

        BASE_URL = "https://mainnet.zklighter.elliot.ai"

        lighter_log.info("=" * 60)
        lighter_log.info("LIGHTER TRADE TEST")
        lighter_log.info("=" * 60)

        # 1. Connect
        lighter_log.info("Connecting to Lighter mainnet...")
        client = lighter.SignerClient(
            url=BASE_URL,
            private_key=api_key_private,
            account_index=account_index,
            api_key_index=api_key_index,
        )

        err = client.check_client()
        if err:
            lighter_log.error(f"Connection failed: {err}")
            await client.close()
            return False

        lighter_log.connection_status("CONNECTED", f"Account #{account_index}")

        # 2. Place market order
        lighter_log.info(f"Placing test order:")
        lighter_log.info(f"  Market index: {MARKET_INDEX}")
        lighter_log.info(f"  Size: {TEST_SIZE} units")
        lighter_log.info(f"  Side: {'BUY' if IS_BUY else 'SELL'}")

        # Create market order
        # market_index: which market (0, 1, 2, etc)
        # client_order_index: unique ID for this order (use timestamp)
        # base_amount: size in base units
        # avg_execution_price: 0 for market orders (will fill at market)
        # is_ask: False for buy, True for sell

        import time
        client_order_index = int(time.time() * 1000) % 1000000  # Unique ID

        create_order, tx_hash, err = await client.create_market_order(
            market_index=MARKET_INDEX,
            client_order_index=client_order_index,
            base_amount=TEST_SIZE,
            avg_execution_price=0,  # 0 = market price
            is_ask=not IS_BUY,  # is_ask=True means SELL, False means BUY
            reduce_only=False,
        )

        if err:
            lighter_log.error(f"Order failed: {err}")
            await client.close()
            return False

        lighter_log.info(f"✅ Order submitted!")
        lighter_log.info(f"   Client Order ID: {client_order_index}")
        lighter_log.info(f"   TX Hash: {tx_hash}")

        # 3. Check positions
        lighter_log.info("Waiting 2 seconds for order to fill...")
        await asyncio.sleep(2)

        # Get positions (if SDK supports it)
        try:
            # Try to get account info
            api_client = lighter.ApiClient(configuration=lighter.Configuration(host=BASE_URL))
            account_api = lighter.AccountApi(api_client)

            # Get account positions
            positions = await account_api.account_positions_by_index(index=account_index)

            if hasattr(positions, 'positions') and positions.positions:
                lighter_log.info(f"Current positions:")
                for pos in positions.positions:
                    if hasattr(pos, 'size') and pos.size != 0:
                        lighter_log.position_update(
                            symbol=f"Market {pos.market_index if hasattr(pos, 'market_index') else '?'}",
                            size=pos.size if hasattr(pos, 'size') else 0,
                            entry_price=pos.avg_price if hasattr(pos, 'avg_price') else 0,
                            unrealized_pnl=pos.unrealized_pnl if hasattr(pos, 'unrealized_pnl') else None
                        )
            else:
                lighter_log.info("No open positions found")

            await api_client.close()

        except Exception as e:
            lighter_log.warning(f"Could not fetch positions: {e}")

        await client.close()

        lighter_log.info("=" * 60)
        lighter_log.info("✅ TEST COMPLETE")
        lighter_log.info("=" * 60)
        lighter_log.info("")
        lighter_log.info("Next steps:")
        lighter_log.info("1. Check position in Lighter UI")
        lighter_log.info("2. Close position manually or wait for bot")
        lighter_log.info("3. Check logs/lighter_*.log for details")

        return True

    except Exception as e:
        lighter_log.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function"""

    # Safety check
    print()
    print("⚠️  " + "=" * 56)
    print("⚠️  REAL MONEY TEST - REVIEW SETTINGS")
    print("⚠️  " + "=" * 56)
    print()
    print(f"  Market Index: {MARKET_INDEX}")
    print(f"  Size: {TEST_SIZE} units")
    print(f"  Side: {'BUY (LONG)' if IS_BUY else 'SELL (SHORT)'}")
    print()
    print("  This will place a REAL order on Lighter mainnet!")
    print()
    response = input("  Continue? (yes/no): ")

    if response.lower() != 'yes':
        print("\n❌ Cancelled")
        return 1

    print()
    success = await test_trade()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
