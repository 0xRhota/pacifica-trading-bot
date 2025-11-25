#!/usr/bin/env python3
"""
Manual test: Place one order on Pacifica to verify the API works
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dexes.pacifica.pacifica_sdk import PacificaSDK
from pacifica_agent.execution.pacifica_executor import PacificaTradeExecutor
from trade_tracker import TradeTracker
import logging
from dotenv import load_dotenv

# Load env vars
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Place one manual test order"""

    # Load credentials
    pacifica_private_key = os.getenv("PACIFICA_API_KEY") or os.getenv("PACIFICA_PRIVATE_KEY")
    pacifica_account = os.getenv("PACIFICA_ACCOUNT")

    if not pacifica_private_key or not pacifica_account:
        logger.error("Missing PACIFICA_API_KEY and/or PACIFICA_ACCOUNT in .env")
        return

    # Initialize SDK
    sdk = PacificaSDK(
        private_key=pacifica_private_key,
        account_address=pacifica_account
    )
    logger.info(f"✅ Account: {pacifica_account}")

    # Initialize executor
    tracker = TradeTracker(dex="pacifica")
    executor = PacificaTradeExecutor(
        pacifica_sdk=sdk,
        trade_tracker=tracker,
        dry_run=False,  # LIVE mode
        default_position_size=10.0,
        max_positions=15
    )

    # Use approximate current price (test)
    symbol = "BTC"
    current_price = 102000.0  # Approximate current BTC price
    logger.info(f"📊 Using test price for {symbol}: ${current_price:,.2f}")

    # Create test decision
    decision = {
        'symbol': symbol,
        'action': 'BUY',
        'current_price': current_price,
        'confidence': 0.75,
        'reasoning': 'Manual test order to verify Pacifica API'
    }

    logger.info(f"🚀 Placing test order: BUY {symbol} @ ${current_price:,.2f}")
    logger.info(f"   Size: $10.00")

    # Execute order
    result = await executor.execute_decision(decision)

    if result:
        logger.info(f"✅ TEST ORDER SUCCESS")
        logger.info(f"   Result: {result}")
    else:
        logger.error(f"❌ TEST ORDER FAILED")

    await sdk.close()

if __name__ == "__main__":
    asyncio.run(main())
