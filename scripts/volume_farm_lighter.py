#!/usr/bin/env python3
"""
Volume Farming Script for Lighter (Extended)
Goal: Generate maximum volume in 5 minutes

MATH:
- Lighter has 0% fees (FREE volume!)
- Each round trip (open + close) = 2x notional volume
- No funding fees if trades closed within minutes

Strategy: Rapid fire open/close on SOL
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from dexes.lighter.lighter_sdk import LighterSDK

# Old Extended bot config (to restore later):
# Command: nohup python3.11 -u -m extended_agent.bot_extended --live --strategy D --interval 300
# Strategy: D (Pairs Trade - Long ETH, Short BTC)
# Position size: $10/leg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger('dexes.lighter').setLevel(logging.WARNING)


class LighterVolumeFarmer:
    """Rapid volume generation via open/close cycles on Lighter (0% fees!)"""

    def __init__(
        self,
        symbol: str = "SOL",
        position_size_usd: float = 50.0,
        duration_minutes: int = 5,
        min_balance: float = 5.0,
    ):
        self.symbol = symbol
        self.position_size_usd = position_size_usd
        self.duration_minutes = duration_minutes
        self.min_balance = min_balance

        # Stats
        self.total_volume = 0.0
        self.total_trades = 0
        self.start_time = None
        self.start_balance = 0.0

        # SDK
        self.sdk = None

    async def initialize(self) -> bool:
        """Initialize SDK with retry for rate limits"""
        try:
            private_key = os.getenv("LIGHTER_PRIVATE_KEY") or os.getenv("LIGHTER_API_KEY_PRIVATE")
            account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "341823"))
            api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))

            if not private_key:
                logger.error("LIGHTER_PRIVATE_KEY not set")
                return False

            self.sdk = LighterSDK(
                private_key=private_key,
                account_index=account_index,
                api_key_index=api_key_index
            )

            # Get initial balance with retries
            for attempt in range(5):
                balance = await self.sdk.get_balance()
                if balance is not None:
                    self.start_balance = balance
                    logger.info(f"Starting balance: ${self.start_balance:.2f}")
                    return True
                logger.warning(f"Balance fetch attempt {attempt+1}/5 failed, waiting...")
                await asyncio.sleep(3)

            logger.error("Could not fetch initial balance after 5 attempts")
            return False
        except Exception as e:
            logger.error(f"Init failed: {e}")
            return False

    async def get_current_price(self) -> float:
        """Get current price for symbol"""
        try:
            # Try to get from positions or orderbook
            positions = await self.sdk.get_positions()
            # If we have a position, use its mark price
            for pos in positions:
                if pos.get('symbol') == self.symbol:
                    return float(pos.get('mark_price', 0))
        except:
            pass

        # Fallback: hardcoded approximate prices
        prices = {"SOL": 195, "ETH": 3400, "BTC": 94000}
        return prices.get(self.symbol, 100)

    async def execute_round_trip(self) -> dict:
        """Execute one open + close cycle"""
        try:
            price = await self.get_current_price()
            size = self.position_size_usd / price

            # Open LONG (side='bid')
            logger.info(f"Opening LONG {size:.4f} {self.symbol} @ ~${price:.2f}")
            open_result = await self.sdk.create_market_order(
                symbol=self.symbol,
                side="bid",
                amount=size,
                reduce_only=False
            )

            if not open_result.get('success'):
                return {'success': False, 'error': f"Open failed: {open_result.get('error')}"}

            # Small delay to ensure position is registered
            await asyncio.sleep(1)

            # Close LONG (side='ask', reduce_only=True)
            logger.info(f"Closing LONG {size:.4f} {self.symbol}")
            close_result = await self.sdk.create_market_order(
                symbol=self.symbol,
                side="ask",
                amount=size,
                reduce_only=True
            )

            if not close_result.get('success'):
                return {'success': False, 'error': f"Close failed: {close_result.get('error')}"}

            # Calculate volume (2 trades = 2x notional)
            volume = self.position_size_usd * 2

            return {
                'success': True,
                'volume': volume,
                'price': price
            }

        except Exception as e:
            logger.error(f"Round trip error: {e}")
            return {'success': False, 'error': str(e)}

    async def check_balance(self) -> float:
        """Check current balance with retry for rate limits"""
        for attempt in range(3):
            try:
                balance = await self.sdk.get_balance()
                if balance is not None:
                    return balance
            except Exception as e:
                if "429" in str(e) or "Rate" in str(e):
                    await asyncio.sleep(3 * (attempt + 1))
                    continue
            await asyncio.sleep(1)
        return self.start_balance  # Return last known balance on failure

    async def run(self):
        """Main farming loop"""
        logger.info("=" * 60)
        logger.info("LIGHTER VOLUME FARMING (0% FEES!)")
        logger.info("=" * 60)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Position size: ${self.position_size_usd}")
        logger.info(f"Duration: {self.duration_minutes} minutes")
        logger.info(f"Min balance: ${self.min_balance}")
        logger.info(f"Fees: $0.00 (Lighter = FREE)")
        logger.info("=" * 60)

        if not await self.initialize():
            return

        self.start_time = datetime.now()
        end_time = self.start_time + timedelta(minutes=self.duration_minutes)

        round_trip_count = 0

        while datetime.now() < end_time:
            # Check balance periodically
            if round_trip_count % 5 == 0:
                current_balance = await self.check_balance()
                if current_balance < self.min_balance:
                    logger.warning(f"Balance ${current_balance:.2f} below min ${self.min_balance} - stopping")
                    break

            # Execute round trip
            result = await self.execute_round_trip()

            if result.get('success'):
                round_trip_count += 1
                self.total_volume += result['volume']
                self.total_trades += 2  # open + close

                elapsed = (datetime.now() - self.start_time).total_seconds()
                logger.info(
                    f"RT#{round_trip_count} | "
                    f"Vol: ${self.total_volume:,.0f} | "
                    f"Trades: {self.total_trades} | "
                    f"Time: {elapsed:.0f}s"
                )
            else:
                logger.error(f"Round trip failed: {result.get('error')}")
                await asyncio.sleep(3)  # Longer pause on error

            # Delay between round trips (avoid rate limits)
            await asyncio.sleep(2)

        # Final stats
        elapsed = (datetime.now() - self.start_time).total_seconds()
        final_balance = await self.check_balance()

        logger.info("")
        logger.info("=" * 60)
        logger.info("FINAL STATS")
        logger.info("=" * 60)
        logger.info(f"Duration: {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
        logger.info(f"Round trips: {round_trip_count}")
        logger.info(f"Total trades: {self.total_trades}")
        logger.info(f"Total volume: ${self.total_volume:,.2f}")
        logger.info(f"Fees paid: $0.00 (Lighter = FREE!)")
        logger.info(f"Start balance: ${self.start_balance:.2f}")
        logger.info(f"End balance: ${final_balance:.2f}")
        logger.info(f"P/L: ${final_balance - self.start_balance:.2f}")
        logger.info("=" * 60)


async def main():
    farmer = LighterVolumeFarmer(
        symbol="SOL",
        position_size_usd=50.0,  # $50 per trade
        duration_minutes=5,  # 5-minute test
        min_balance=5.0,  # Stop if below $5
    )
    await farmer.run()


if __name__ == "__main__":
    asyncio.run(main())
