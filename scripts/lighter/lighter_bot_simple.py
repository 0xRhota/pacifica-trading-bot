#!/usr/bin/env python3
"""
Simple Lighter Bot - Quick Test
Opens a small position on Lighter to verify everything works
Run this while Pacifica bot keeps running
"""

import asyncio
import os
from dotenv import load_dotenv
from utils.dex_logger import MultiDEXLogger

load_dotenv()

# Initialize logger
logger = MultiDEXLogger()
lighter_log = logger.lighter

async def test_lighter_position():
    """Test opening and managing a position on Lighter"""

    try:
        import lighter

        # Load config
        api_key_private = os.getenv("LIGHTER_API_KEY_PRIVATE")
        account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX"))
        api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX"))

        BASE_URL = "https://mainnet.zklighter.elliot.ai"

        lighter_log.info("=" * 60)
        lighter_log.info("LIGHTER BOT TEST - SIMPLE POSITION")
        lighter_log.info("=" * 60)

        # 1. Connect
        lighter_log.info("Connecting to Lighter mainnet...")
        client = lighter.SignerClient(
            url=BASE_URL,
            private_key=api_key_private,
            account_index=account_index,
            api_key_index=api_key_index,
        )

        # Verify connection
        err = client.check_client()
        if err:
            lighter_log.error(f"Connection failed: {err}")
            return False

        lighter_log.connection_status("CONNECTED", f"Account #{account_index}")

        # 2. Get available markets
        lighter_log.info("Fetching available markets...")
        api_client = lighter.ApiClient(configuration=lighter.Configuration(host=BASE_URL))

        # Check account balance first
        lighter_log.info("Checking account balance...")

        # For now, just log that we're ready
        lighter_log.info("✅ Connection successful")
        lighter_log.info("📊 Ready to place test order")
        lighter_log.info("")
        lighter_log.info("⚠️  NEXT STEP: Check your Lighter account balance")
        lighter_log.info("⚠️  Then uncomment the order placement code below")
        lighter_log.info("")

        # TODO: Uncomment after confirming balance
        # Example order (very small for testing):
        # result = await client.create_market_order(
        #     base_amount=10,  # Very small size for testing
        #     price=0,  # Market price (0 for market orders)
        #     client_order_index=1,
        #     order_type=lighter.ORDER_TYPE_MARKET,
        #     time_in_force=lighter.TIME_IN_FORCE_IOC
        # )

        await client.close()
        await api_client.close()

        return True

    except Exception as e:
        lighter_log.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function"""
    success = await test_lighter_position()

    if success:
        lighter_log.info("=" * 60)
        lighter_log.info("✅ TEST COMPLETE")
        lighter_log.info("Check logs/lighter_*.log for details")
        lighter_log.info("=" * 60)
    else:
        lighter_log.error("❌ TEST FAILED")

    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
