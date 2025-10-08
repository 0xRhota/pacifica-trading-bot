#!/usr/bin/env python3
"""
Live Trading Bot for Lighter - Uses same long/short strategy
Checks positions every 45s, opens new positions every 15min
"""

import asyncio
import logging
import signal
import sys
import time
import os
import math
import random
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dexes.lighter.lighter_sdk import LighterSDK
from strategies.long_short import LongShortStrategy
from pacifica_bot import PacificaAPI, TradingConfig
from config import BotConfig

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("live_lighter_output.log")
    ]
)

logger = logging.getLogger(__name__)


class LiveLighterBot:
    """Live trading bot for Lighter DEX"""

    def __init__(self, sdk: LighterSDK, strategy, pacifica_api: PacificaAPI):
        self.sdk = sdk
        self.strategy = strategy
        self.pacifica_api = pacifica_api  # For orderbook data
        self.open_positions = {}  # symbol -> market_id
        self.last_trade_time = 0
        self.running = False

        # Lighter-specific settings
        self.symbols = ["SOL"]  # Start with SOL only
        self.min_position_usd = 10.0
        self.max_position_usd = 15.0
        self.check_frequency = 45  # seconds
        self.trade_frequency = 900  # 15 minutes

    async def start(self):
        """Start live trading"""
        logger.info("🔴 STARTING LIGHTER LIVE TRADING BOT")
        logger.info(f"⚠️  THIS WILL PLACE REAL ORDERS WITH REAL MONEY")
        logger.info(f"🎯 Strategy: {self.strategy.__class__.__name__}")
        logger.info(f"Check frequency: {self.check_frequency}s")
        logger.info(f"Trade frequency: {self.trade_frequency}s ({self.trade_frequency/60:.0f} min)")
        logger.info(f"Position sizes: ${self.min_position_usd}-${self.max_position_usd}")

        self.running = True

        # Get account info
        balance = await self.sdk.get_balance()
        if balance:
            logger.info(f"💰 Balance: ${balance:.2f}")

        # Load existing positions
        await self._sync_positions()

        # Main loop
        while self.running:
            try:
                await self._check_and_manage_positions()
                await self._maybe_open_new_position()
                await asyncio.sleep(self.check_frequency)
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _sync_positions(self):
        """Sync local position tracking with Lighter API"""
        result = await self.sdk.get_positions()

        if not result.get('success'):
            logger.error("Failed to get positions from Lighter API")
            return

        positions = result.get('data', [])

        if positions:
            logger.info(f"📊 Found {len(positions)} existing positions")
            for pos in positions:
                market_id = pos['market_id']
                symbol = {2: 'SOL', 1: 'BTC', 3: 'ETH'}.get(market_id, f'Market{market_id}')
                logger.info(f"   {symbol}: {pos['size']:.4f} @ ${pos['entry_price']:.2f}")
                logger.warning(f"   ⚠️  Position opened outside bot - will monitor but not auto-close")
        else:
            logger.info("✅ No existing positions - clean start")

    async def _check_and_manage_positions(self):
        """Check positions - Lighter doesn't support auto-close yet, just monitor"""
        result = await self.sdk.get_positions()

        if not result.get('success'):
            return

        positions = result.get('data', [])

        if positions:
            logger.info(f"🔍 Monitoring {len(positions)} positions...")
            for pos in positions:
                market_id = pos['market_id']
                symbol = {2: 'SOL', 1: 'BTC', 3: 'ETH'}.get(market_id, f'Market{market_id}')
                logger.info(f"   {symbol}: {pos['size']:.4f} @ ${pos['entry_price']:.2f}, P&L: ${pos['pnl']:.4f}")

    async def _maybe_open_new_position(self):
        """Open new position if conditions met"""
        time_since_last = time.time() - self.last_trade_time

        if time_since_last < self.trade_frequency:
            return

        # Get balance
        balance = await self.sdk.get_balance()
        if not balance:
            logger.warning("Could not get balance")
            return

        logger.info(f"💰 Balance: ${balance:.2f}")

        # Choose symbol
        symbol = random.choice(self.symbols)

        try:
            # Get Pacifica data for strategy (using Pacifica API for orderbook)
            price = await self.pacifica_api.get_market_price(symbol)
            if not price:
                logger.warning(f"Could not get price for {symbol}")
                return

            orderbook = await self.pacifica_api.get_orderbook(symbol)
            if not orderbook:
                logger.warning(f"Could not get orderbook for {symbol}")
                return

            # Use strategy to decide direction
            should_open, side = self.strategy.should_open_position(
                symbol, price, orderbook, {'balance': balance}
            )

            if not should_open or not side:
                return

            # Calculate position size
            position_value = random.uniform(self.min_position_usd, self.max_position_usd)
            size = position_value / price

            # Round to appropriate decimals for Lighter
            if symbol == "SOL":
                size = round(size, 3)  # 3 decimals for SOL
                if size < 0.050:
                    size = 0.050  # Minimum size
            elif symbol == "BTC":
                size = round(size, 6)
                if size < 0.001:
                    size = 0.001
            elif symbol == "ETH":
                size = round(size, 4)
                if size < 0.01:
                    size = 0.01

            actual_value = size * price

            # Verify meets minimum
            if actual_value < 10:
                logger.warning(f"Position too small: ${actual_value:.2f} < $10")
                return

            # Safety check
            if actual_value > self.max_position_usd * 2:
                logger.error(f"❌ Position too large: ${actual_value:.2f} > ${self.max_position_usd * 2:.2f}")
                return

            logger.info(f"🟢 Opening {side} position for {symbol}")
            logger.info(f"   Price: ${price:.2f}, Size: {size:.6f}, Value: ${actual_value:.2f}")

            # Place order via Lighter SDK
            result = await self.sdk.create_market_order(
                symbol=symbol,
                side=side,
                amount=size
            )

            if result.get('success'):
                logger.info(f"✅ Lighter order placed: {result['tx_hash'][:32]}...")
                self.last_trade_time = time.time()
            else:
                logger.error(f"❌ Order failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error opening position: {e}", exc_info=True)

    async def stop(self):
        """Stop bot"""
        logger.info("🛑 Stopping Lighter bot...")
        self.running = False
        await self.sdk.close()


async def main():
    """Main entry point"""
    print("="*60)
    print("⚠️  LIGHTER LIVE TRADING BOT")
    print("="*60)
    print("This will place REAL orders with REAL money on Lighter!")
    print("Position sizes: $10-$15")
    print("Check every: 45s")
    print("Trade every: 15 minutes")
    print("="*60)
    print()

    # Initialize Lighter SDK
    sdk = LighterSDK(
        private_key=os.getenv("LIGHTER_API_KEY_PRIVATE"),
        account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX")),
        api_key_index=int(os.getenv("LIGHTER_API_KEY_INDEX"))
    )

    logger.info(f"✅ Lighter SDK initialized: Account #{os.getenv('LIGHTER_ACCOUNT_INDEX')}")

    # Initialize strategy
    strategy = LongShortStrategy()

    # Initialize Pacifica API for orderbook data
    pacifica_config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL,
        symbols=["SOL"]
    )
    pacifica_api = PacificaAPI(pacifica_config)
    await pacifica_api.__aenter__()

    # Create bot
    bot = LiveLighterBot(sdk, strategy, pacifica_api)

    # Signal handlers
    def signal_handler(sig, frame):
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await bot.stop()
        await pacifica_api.__aexit__(None, None, None)

if __name__ == "__main__":
    asyncio.run(main())
