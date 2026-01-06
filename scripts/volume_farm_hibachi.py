#!/usr/bin/env python3
"""
Volume Farming Script for Hibachi
Goal: Generate maximum volume in 10 minutes

MATH:
- $35 balance at 10x = $350 max notional
- Each round trip (open + close) = $700 volume
- 0.035% fee per trade = $0.245 per round trip
- To get $50k volume: ~71 round trips, ~$17.50 in fees

FUNDING: $0 (positions held < 1 minute, funding is every 8 hours)

Strategy: Rapid fire open/close on volatile asset (SOL)
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from dexes.hibachi.hibachi_sdk import HibachiSDK

# Old Hibachi bot config (to restore later):
# Command: nohup python3 -u -m hibachi_agent.bot_hibachi --live --interval 600
# Strategy: v9_qwen_enhanced
# Model: qwen-max

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger('dexes.hibachi').setLevel(logging.WARNING)


class VolumeFarmer:
    """Rapid volume generation via open/close cycles"""

    def __init__(
        self,
        symbol: str = "SOL/USDT-P",
        position_size_usd: float = 100.0,  # Small to allow many trades
        leverage: int = 10,
        duration_minutes: int = 10,
        min_balance: float = 5.0,  # Stop if balance drops below this
    ):
        self.symbol = symbol
        self.position_size_usd = position_size_usd
        self.leverage = leverage
        self.duration_minutes = duration_minutes
        self.min_balance = min_balance

        # Stats
        self.total_volume = 0.0
        self.total_trades = 0
        self.total_fees_est = 0.0
        self.start_time = None
        self.start_balance = 0.0

        # SDK
        self.sdk = None

    async def initialize(self) -> bool:
        """Initialize SDK with retry for rate limits"""
        try:
            api_key = os.getenv("HIBACHI_PUBLIC_KEY")
            api_secret = os.getenv("HIBACHI_PRIVATE_KEY")
            account_id = os.getenv("HIBACHI_ACCOUNT_ID")

            if not api_key or not api_secret:
                logger.error("HIBACHI credentials not set")
                return False

            self.sdk = HibachiSDK(
                api_key=api_key,
                api_secret=api_secret,
                account_id=account_id
            )

            # Get initial balance with retries
            for attempt in range(5):
                balance = await self.sdk.get_balance()
                if balance is not None:
                    self.start_balance = balance
                    logger.info(f"Starting balance: ${self.start_balance:.2f}")
                    return True
                logger.warning(f"Balance fetch attempt {attempt+1}/5 failed, waiting...")
                await asyncio.sleep(5)

            logger.error("Could not fetch initial balance after 5 attempts")
            return False
        except Exception as e:
            logger.error(f"Init failed: {e}")
            return False

    async def get_current_price(self) -> float:
        """Get current price for symbol"""
        try:
            # Get from orderbook - use full symbol format
            orderbook = await self.sdk.get_orderbook(self.symbol)
            if orderbook:
                bids = orderbook.get('bids', [])
                asks = orderbook.get('asks', [])
                if bids and asks:
                    return (float(bids[0][0]) + float(asks[0][0])) / 2
        except:
            pass

        # Fallback: hardcoded approximate
        prices = {"SOL": 195, "ETH": 3400, "BTC": 94000}
        base = self.symbol.split("/")[0]
        return prices.get(base, 100)

    async def execute_round_trip(self) -> dict:
        """Execute one open + close cycle"""
        try:
            price = await self.get_current_price()
            size = self.position_size_usd / price

            # Open LONG (is_buy=True)
            logger.info(f"📈 Opening LONG {size:.4f} {self.symbol} @ ~${price:.2f}")
            open_result = await self.sdk.create_market_order(
                symbol=self.symbol,
                is_buy=True,
                amount=size
            )

            if not open_result:
                return {'success': False, 'error': 'Open failed'}

            # Small delay to ensure position is registered
            await asyncio.sleep(0.5)

            # Close LONG (is_buy=False to sell)
            logger.info(f"📉 Closing LONG {size:.4f} {self.symbol}")
            close_result = await self.sdk.create_market_order(
                symbol=self.symbol,
                is_buy=False,
                amount=size
            )

            if not close_result:
                return {'success': False, 'error': 'Close failed'}

            # Calculate volume (2 trades = 2x notional)
            volume = self.position_size_usd * 2
            fee_est = volume * 0.00035  # 0.035% per trade

            return {
                'success': True,
                'volume': volume,
                'fee_est': fee_est,
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
                    await asyncio.sleep(5 * (attempt + 1))
                    continue
            await asyncio.sleep(1)
        return self.start_balance  # Return last known balance on failure

    async def run(self):
        """Main farming loop"""
        logger.info("=" * 60)
        logger.info("HIBACHI VOLUME FARMING EXPERIMENT")
        logger.info("=" * 60)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Position size: ${self.position_size_usd}")
        logger.info(f"Leverage: {self.leverage}x")
        logger.info(f"Duration: {self.duration_minutes} minutes")
        logger.info(f"Min balance: ${self.min_balance}")
        logger.info("=" * 60)

        if not await self.initialize():
            return

        self.start_time = datetime.now()
        end_time = self.start_time + timedelta(minutes=self.duration_minutes)

        round_trip_count = 0

        while datetime.now() < end_time:
            # Check balance
            current_balance = await self.check_balance()
            if current_balance < self.min_balance:
                logger.warning(f"⚠️ Balance ${current_balance:.2f} below min ${self.min_balance} - stopping")
                break

            # Execute round trip
            result = await self.execute_round_trip()

            if result.get('success'):
                round_trip_count += 1
                self.total_volume += result['volume']
                self.total_trades += 2  # open + close
                self.total_fees_est += result['fee_est']

                elapsed = (datetime.now() - self.start_time).total_seconds()
                logger.info(
                    f"✅ RT#{round_trip_count} | "
                    f"Vol: ${self.total_volume:,.0f} | "
                    f"Trades: {self.total_trades} | "
                    f"Fees: ${self.total_fees_est:.2f} | "
                    f"Time: {elapsed:.0f}s"
                )
            else:
                logger.error(f"❌ Round trip failed: {result.get('error')}")
                await asyncio.sleep(2)  # Longer pause on error

            # Longer delay between round trips to avoid rate limits
            await asyncio.sleep(3)

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
        logger.info(f"Estimated fees: ${self.total_fees_est:.2f}")
        logger.info(f"Start balance: ${self.start_balance:.2f}")
        logger.info(f"End balance: ${final_balance:.2f}")
        logger.info(f"P/L: ${final_balance - self.start_balance:.2f}")
        logger.info("=" * 60)


async def main():
    farmer = VolumeFarmer(
        symbol="SOL/USDT-P",
        position_size_usd=50.0,  # $50 per trade (conservative)
        leverage=10,
        duration_minutes=5,  # 5-minute test
        min_balance=5.0,  # Stop if below $5
    )
    await farmer.run()


if __name__ == "__main__":
    asyncio.run(main())
