#!/usr/bin/env python3
"""
Volume Farming Script for Extended (x10 exchange)
Goal: Generate maximum volume in 5 minutes

Strategy: Rapid fire open/close on SOL
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Old Extended bot config (to restore later):
# Command: nohup python3.11 -u -m extended_agent.bot_extended --live --strategy D --interval 300
# Strategy: D (Pairs Trade - Long ETH, Short BTC)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class ExtendedVolumeFarmer:
    """Rapid volume generation via open/close cycles on Extended"""

    def __init__(
        self,
        symbol: str = "SOL-USD",
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
        self.client = None

    async def initialize(self) -> bool:
        """Initialize x10 trading client"""
        try:
            from x10.perpetual.accounts import StarkPerpetualAccount
            from x10.perpetual.configuration import MAINNET_CONFIG
            from x10.perpetual.trading_client import PerpetualTradingClient

            api_key = os.getenv("EXTENDED") or os.getenv("EXTENDED_API_KEY")
            private_key = os.getenv("EXTENDED_STARK_PRIVATE_KEY")
            public_key = os.getenv("EXTENDED_STARK_PUBLIC_KEY")
            vault = os.getenv("EXTENDED_VAULT")

            if not all([api_key, private_key, public_key, vault]):
                logger.error("Missing Extended credentials")
                return False

            config = MAINNET_CONFIG
            stark_account = StarkPerpetualAccount(
                vault=int(vault),
                private_key=private_key,
                public_key=public_key,
                api_key=api_key,
            )

            self.client = PerpetualTradingClient(
                endpoint_config=config,
                stark_account=stark_account
            )

            # Get initial balance
            balance = await self.client.account.get_balance()
            if balance and balance.data:
                self.start_balance = float(balance.data.equity)
                logger.info(f"Starting balance: ${self.start_balance:.2f}")
                return True

            logger.error("Could not fetch account info")
            return False
        except Exception as e:
            logger.error(f"Init failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def get_current_price(self) -> float:
        """Get current price for symbol"""
        try:
            stats = await self.client.markets_info.get_market_statistics(market_name=self.symbol)
            if stats and stats.data:
                return float(stats.data.last_price)
        except:
            pass

        # Fallback prices
        prices = {"SOL-USD": 195, "ETH-USD": 3400, "BTC-USD": 94000}
        return prices.get(self.symbol, 100)

    async def execute_round_trip(self) -> dict:
        """Execute one open + close cycle"""
        try:
            from x10.perpetual.orders import OrderSide, TimeInForce

            price = await self.get_current_price()
            if price <= 0:
                return {'success': False, 'error': 'Could not get price'}

            # Calculate size with proper precision (SOL=2 decimals, ETH=3, BTC=5)
            raw_size = self.position_size_usd / price
            if "SOL" in self.symbol:
                size = round(raw_size, 2)  # SOL: min 0.01
            elif "ETH" in self.symbol:
                size = round(raw_size, 3)  # ETH: min 0.001
            else:
                size = round(raw_size, 5)  # BTC: min 0.00001

            order_price = price * 1.01  # 1% above for market-like fill

            # Open LONG
            logger.info(f"Opening LONG {size:.4f} {self.symbol} @ ~${price:.2f}")
            open_order = await self.client.place_order(
                market_name=self.symbol,
                amount_of_synthetic=Decimal(str(size)),
                price=Decimal(str(int(order_price))),
                side=OrderSide.BUY,
                time_in_force=TimeInForce.IOC,  # Immediate or cancel for fast fills
            )

            if not open_order or not open_order.data:
                return {'success': False, 'error': 'Open failed'}

            # Small delay
            await asyncio.sleep(0.5)

            # Close LONG
            close_price = price * 0.99  # 1% below for market-like fill
            logger.info(f"Closing LONG {size:.4f} {self.symbol}")
            close_order = await self.client.place_order(
                market_name=self.symbol,
                amount_of_synthetic=Decimal(str(size)),
                price=Decimal(str(int(close_price))),
                side=OrderSide.SELL,
                reduce_only=True,
                time_in_force=TimeInForce.IOC,
            )

            if not close_order or not close_order.data:
                return {'success': False, 'error': 'Close failed'}

            # Calculate volume
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
        """Check current balance"""
        try:
            balance = await self.client.account.get_balance()
            if balance and balance.data:
                return float(balance.data.equity)
        except:
            pass
        return self.start_balance

    async def run(self):
        """Main farming loop"""
        logger.info("=" * 60)
        logger.info("EXTENDED VOLUME FARMING")
        logger.info("=" * 60)
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Position size: ${self.position_size_usd}")
        logger.info(f"Duration: {self.duration_minutes} minutes")
        logger.info(f"Min balance: ${self.min_balance}")
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
                self.total_trades += 2

                elapsed = (datetime.now() - self.start_time).total_seconds()
                logger.info(
                    f"RT#{round_trip_count} | "
                    f"Vol: ${self.total_volume:,.0f} | "
                    f"Trades: {self.total_trades} | "
                    f"Time: {elapsed:.0f}s"
                )
            else:
                logger.error(f"Round trip failed: {result.get('error')}")
                await asyncio.sleep(2)

            # Delay between round trips
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
        logger.info(f"Start balance: ${self.start_balance:.2f}")
        logger.info(f"End balance: ${final_balance:.2f}")
        logger.info(f"P/L: ${final_balance - self.start_balance:.2f}")
        logger.info("=" * 60)


async def main():
    farmer = ExtendedVolumeFarmer(
        symbol="SOL-USD",
        position_size_usd=50.0,
        duration_minutes=15,  # Extended to 15 minutes
        min_balance=5.0,
    )
    await farmer.run()


if __name__ == "__main__":
    asyncio.run(main())
