#!/usr/bin/env python3
"""
Lighter VWAP Bot - 6 Symbols, Both Directions, High Volume
Checks every 5 minutes for maximum volume
"""

import asyncio
import logging
import signal
import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Add root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dexes.lighter.lighter_sdk import LighterSDK
from strategies.vwap_strategy import VWAPStrategy
from pacifica_bot import PacificaAPI, TradingConfig

# Load environment
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("live_bot_vwap_lighter.log")
    ]
)

logger = logging.getLogger(__name__)


class LighterVWAPBot:
    """VWAP trading bot for Lighter - 6 symbols, 5-minute checks"""

    def __init__(self, lighter_sdk: LighterSDK, config: TradingConfig):
        self.lighter_sdk = lighter_sdk
        self.config = config
        self.pacifica_api = PacificaAPI(config)  # For orderbook data
        self.strategy = VWAPStrategy(imbalance_threshold=1.3)

        # Trading symbols
        self.symbols = ["SOL", "BTC", "ETH", "PENGU", "XPL", "ASTER"]

        # Track open positions
        self.open_positions = {}  # symbol -> {order_id, entry_price, size, side, entry_time}

        # Check frequency: 5 minutes
        self.check_interval = 5 * 60  # 300 seconds

        self.running = False

    async def start(self):
        """Start the bot"""
        logger.info("=" * 70)
        logger.info("🚀 STARTING LIGHTER VWAP BOT")
        logger.info("=" * 70)
        logger.info(f"Strategy: VWAP + Orderbook (Long & Short)")
        logger.info(f"Symbols: {', '.join(self.symbols)}")
        logger.info(f"Check interval: {self.check_interval}s (5 minutes)")
        logger.info(f"Imbalance threshold: 1.5x")
        logger.info(f"Position size: $20 per trade")
        logger.info("=" * 70)

        # Get initial balance
        balance = await self.lighter_sdk.get_balance()
        if balance:
            logger.info(f"💰 Lighter Balance: ${balance:.2f}")

        self.running = True

        async with self.pacifica_api:
            while self.running:
                try:
                    await self._trading_cycle()

                    # Sleep until next cycle
                    logger.info(f"\n⏰ Next check in {self.check_interval}s...")
                    await asyncio.sleep(self.check_interval)

                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}", exc_info=True)
                    await asyncio.sleep(10)

    async def _trading_cycle(self):
        """One complete trading cycle - check all 6 symbols"""
        logger.info("\n" + "=" * 70)
        logger.info(f"📊 TRADING CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)

        # Check each symbol
        for symbol in self.symbols:
            try:
                await self._check_symbol(symbol)
            except Exception as e:
                logger.error(f"Error checking {symbol}: {e}", exc_info=True)
                continue

        # Show summary
        logger.info("\n" + "-" * 70)
        logger.info(f"Open positions: {len(self.open_positions)}")
        for symbol, pos in self.open_positions.items():
            logger.info(f"  {symbol}: {pos['side']} {pos['size']} @ ${pos['entry_price']}")
        logger.info("-" * 70)

    async def _check_symbol(self, symbol: str):
        """Check one symbol for trading opportunity"""
        logger.info(f"\n[{symbol}]")

        # Get current price from orderbook
        orderbook = await self.pacifica_api.get_orderbook(symbol)
        if not orderbook:
            logger.warning(f"  No orderbook for {symbol}")
            return

        current_price = await self.pacifica_api.get_market_price(symbol)
        if not current_price:
            logger.warning(f"  No price for {symbol}")
            return

        # Check if should open position
        if symbol not in self.open_positions:
            should_open, side = self.strategy.should_open_position(
                symbol, current_price, orderbook, {}
            )

            if should_open:
                await self._open_position(symbol, side, current_price)

    async def _open_position(self, symbol: str, side: str, current_price: float):
        """Open new position with SL and TP"""
        logger.info(f"\n🎯 Opening {side.upper()} position on {symbol}")

        # Get position size
        size = self.strategy.get_position_size(symbol, current_price, {})

        logger.info(f"  Size: {size} {symbol}")
        logger.info(f"  Value: ~${size * current_price:.2f}")

        # Place market order
        result = await self.lighter_sdk.create_market_order(
            symbol=symbol,
            side=side,
            amount=size
        )

        if not result.get('success'):
            logger.error(f"  ❌ Order failed: {result.get('error')}")
            return

        logger.info(f"  ✅ Order placed: {result.get('tx_hash')}")

        # Determine if long or short
        is_long = (side == 'bid')

        # Set stop-loss (1%)
        sl_result = await self.lighter_sdk.create_stop_loss_order(
            symbol=symbol,
            position_size=size,
            entry_price=current_price,
            is_long=is_long,
            stop_loss_pct=0.01
        )

        if sl_result.get('success'):
            logger.info(f"  ✅ Stop-loss set at 1%")
        else:
            logger.warning(f"  ⚠️  Stop-loss failed: {sl_result.get('error')}")

        # Set take-profit (3% for 3:1 risk/reward)
        tp_result = await self.lighter_sdk.create_take_profit_order(
            symbol=symbol,
            position_size=size,
            entry_price=current_price,
            is_long=is_long,
            take_profit_pct=0.03
        )

        if tp_result.get('success'):
            logger.info(f"  ✅ Take-profit set at 3%")
        else:
            logger.warning(f"  ⚠️  Take-profit failed: {tp_result.get('error')}")

        # Track position
        self.open_positions[symbol] = {
            'side': 'buy' if is_long else 'sell',
            'size': size,
            'entry_price': current_price,
            'entry_time': time.time(),
            'tx_hash': result.get('tx_hash')
        }

        logger.info(f"  📝 Position tracked")

    def stop(self):
        """Stop the bot gracefully"""
        logger.info("\n🛑 Stopping bot...")
        self.running = False


async def main():
    # Initialize Lighter SDK
    lighter_sdk = LighterSDK(
        private_key=os.getenv("LIGHTER_API_KEY_PRIVATE"),
        account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX")),
        api_key_index=int(os.getenv("LIGHTER_API_KEY_INDEX"))
    )

    # Initialize Pacifica API (for orderbook data)
    config = TradingConfig(
        api_key=os.getenv("PACIFICA_API_KEY", ""),
        base_url="https://api.pacifica.fi/api/v1"
    )

    # Create bot
    bot = LighterVWAPBot(lighter_sdk, config)

    # Setup signal handlers
    def signal_handler(sig, frame):
        bot.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.start()
    finally:
        await lighter_sdk.close()
        logger.info("✅ Bot stopped cleanly")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
