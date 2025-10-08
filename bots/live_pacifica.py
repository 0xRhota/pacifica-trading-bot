#!/usr/bin/env python3
"""
Pacifica Trading Bot - Enhanced Orderbook Strategy
Larger positions, ladder TP, smart filters
"""

import asyncio
import logging
import signal
import sys
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# Add root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pacifica_bot import PacificaAPI, TradingConfig
from dexes.pacifica.pacifica_sdk import PacificaSDK
from risk_manager import RiskManager
from trade_tracker import tracker
from config import BotConfig
from strategies.long_short import LongShortStrategy

# Load environment
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/pacifica.log")
    ]
)

logger = logging.getLogger(__name__)

class PacificaTradingBot:
    """Enhanced Pacifica trading bot with ladder TP and smart filters"""

    def __init__(self, sdk: PacificaSDK, config: TradingConfig, strategy=None):
        self.sdk = sdk
        self.config = config
        self.api = PacificaAPI(config)
        self.risk_manager = RiskManager(BotConfig)
        self.strategy = strategy or LongShortStrategy()
        self.open_positions = {}  # symbol -> order_id
        self.last_trade_time = 0
        self.running = False

    async def start(self):
        """Start live trading"""
        logger.info("=" * 70)
        logger.info("🚀 STARTING ENHANCED PACIFICA BOT")
        logger.info("=" * 70)
        logger.info(f"Strategy: {self.strategy.__class__.__name__}")
        logger.info(f"Position size: ${BotConfig.MIN_POSITION_SIZE_USD}-${BotConfig.MAX_POSITION_SIZE_USD}")
        logger.info(f"Ladder TP: {BotConfig.LADDER_TP_LEVELS} (sizes: {BotConfig.LADDER_TP_SIZES})")
        logger.info(f"Stop loss: {BotConfig.MAX_LOSS_THRESHOLD*100:.1f}%")
        logger.info(f"Max spread: {BotConfig.MAX_SPREAD_PCT}%")
        logger.info(f"Min orders: {BotConfig.MIN_ORDER_COUNT}")
        logger.info(f"Weighted depth: {BotConfig.WEIGHTED_DEPTH}")
        logger.info(f"Time limit: {'None (let winners run!)' if BotConfig.MAX_POSITION_HOLD_TIME is None else f'{BotConfig.MAX_POSITION_HOLD_TIME}s'}")
        logger.info("=" * 70)

        self.running = True

        async with self.api:
            # Get account info
            account = await self.api.get_account_info(BotConfig.ACCOUNT_ADDRESS)
            if account:
                logger.info(f"💰 Balance: ${float(account.get('balance', 0)):.2f}")
                logger.info(f"💰 Equity: ${float(account.get('account_equity', 0)):.2f}")

            # Load existing positions
            await self._sync_positions_from_api()

            # Main loop
            while self.running:
                try:
                    await self._check_and_manage_positions()
                    await self._maybe_open_new_position()
                    await asyncio.sleep(BotConfig.CHECK_FREQUENCY_SECONDS)
                except Exception as e:
                    logger.error(f"Error in trading cycle: {e}", exc_info=True)
                    await asyncio.sleep(10)

    async def _sync_positions_from_api(self):
        """Load positions from Pacifica API on startup"""
        try:
            # SDK get_positions() doesn't take parameters
            result = self.sdk.get_positions()
            positions = result.get('data', []) if result else []
            if positions:
                for pos in positions:
                    symbol = pos.get('symbol')
                    size = float(pos.get('position', 0))
                    if size != 0:
                        self.open_positions[symbol] = pos.get('order_id')
                        logger.info(f"📊 Found existing position: {symbol} {size}")
        except Exception as e:
            logger.error(f"Error syncing positions: {e}")

    async def _check_and_manage_positions(self):
        """Check all open positions for exit signals"""
        if not self.open_positions:
            return

        logger.info(f"🔍 Checking {len(self.open_positions)} positions...")

        symbols_to_close = []

        for symbol, order_id in list(self.open_positions.items()):
            try:
                # Get current price and position
                current_price = await self.api.get_market_price(symbol)
                if not current_price:
                    continue

                # Get position details from tracker
                trade = None
                for t in tracker.get_open_trades():
                    if t.get('order_id') == order_id:
                        trade = t
                        break

                if not trade:
                    # Position not in tracker, remove from tracking
                    logger.warning(f"⚠️  {symbol} position {order_id} not in tracker")
                    symbols_to_close.append(symbol)
                    continue

                # Calculate time held (timestamp is ISO string, convert to unix time)
                from datetime import datetime
                trade_time = datetime.fromisoformat(trade['timestamp']).timestamp()
                time_held = time.time() - trade_time

                # Check if should close
                should_close, reason = self.strategy.should_close_position(
                    trade, current_price, time_held
                )

                if should_close:
                    logger.info(f"🔔 Closing {symbol}: {reason}")
                    await self._close_position(symbol, trade, reason)
                    symbols_to_close.append(symbol)

            except Exception as e:
                logger.error(f"Error checking position {symbol}: {e}")
                continue

        # Remove closed positions
        for symbol in symbols_to_close:
            self.open_positions.pop(symbol, None)

    async def _close_position(self, symbol: str, trade: dict, reason: str):
        """Close a position"""
        try:
            # Close via SDK (SDK is synchronous, not async)
            result = self.sdk.close_position(symbol)

            if result and result.get('success'):
                logger.info(f"✅ {symbol} closed: {reason}")
                # Log exit with current price
                current_price = await self.api.get_market_price(symbol)
                tracker.log_exit(trade['order_id'], current_price, exit_reason=reason)
            else:
                logger.error(f"❌ Failed to close {symbol}")

        except Exception as e:
            logger.error(f"Error closing {symbol}: {e}")

    async def _maybe_open_new_position(self):
        """Check if should open new position (respects trade frequency)"""
        current_time = time.time()

        # Check trade frequency
        if current_time - self.last_trade_time < BotConfig.TRADE_FREQUENCY_SECONDS:
            return

        # Get account info
        account = await self.api.get_account_info(BotConfig.ACCOUNT_ADDRESS)
        if not account:
            return

        logger.info(f"💰 Balance: ${float(account.get('balance', 0)):.2f}, Equity: ${float(account.get('account_equity', 0)):.2f}, Leverage: {float(account.get('leverage', 0)):.2f}x")

        # Try each symbol in rotation
        for symbol in BotConfig.TRADING_SYMBOLS:
            # Skip if already have position
            if symbol in self.open_positions:
                continue

            try:
                # Get market data
                current_price = await self.api.get_market_price(symbol)
                orderbook = await self.api.get_orderbook(symbol)

                if not current_price or not orderbook:
                    continue

                # Check if should open position
                should_open, side = self.strategy.should_open_position(
                    symbol, current_price, orderbook, account
                )

                if should_open:
                    await self._open_position(symbol, side, current_price, account)
                    self.last_trade_time = current_time
                    break  # Only open one position per cycle

            except Exception as e:
                logger.error(f"Error checking {symbol}: {e}")
                continue

    async def _open_position(self, symbol: str, side: str, current_price: float, account: dict):
        """Open new position"""
        try:
            # Get position size
            size = self.strategy.get_position_size(symbol, current_price, account)
            position_value = size * current_price

            # Check risk limits
            if position_value > BotConfig.MAX_POSITION_SIZE_USD:
                logger.warning(f"⚠️  {symbol} minimum lot size (${position_value:.2f}) exceeds max position (${BotConfig.MAX_POSITION_SIZE_USD}), skipping")
                return

            logger.info(f"🟢 Opening {side} position for {symbol}")
            logger.info(f"   Price: ${current_price:.2f}, Size: {size:.6f}, Value: ${position_value:.2f}")

            # Place order (SDK is synchronous, not async)
            # SDK signature: create_market_order(symbol, side, amount)
            result = self.sdk.create_market_order(symbol, side, str(size))

            logger.info(f"SDK Response: {result}")

            # Extract order_id from response (nested in 'data' field)
            order_id = None
            if isinstance(result, dict) and result.get('success'):
                data = result.get('data', {})
                order_id = data.get('order_id')

            if order_id:
                logger.info(f"✅ Order placed: #{order_id}")

                # Track position
                self.open_positions[symbol] = order_id

                # Record in tracker
                tracker.log_entry(
                    order_id=order_id,
                    symbol=symbol,
                    side="buy" if side == "bid" else "sell",  # Convert bid/ask to buy/sell
                    size=size,
                    entry_price=current_price
                )

                logger.info(f"Trade opened: {symbol} {side} {size:.6f} @ ${current_price:.4f}")
            else:
                logger.error(f"❌ Order failed")

        except Exception as e:
            logger.error(f"Error opening position: {e}", exc_info=True)

    def stop(self):
        """Stop the bot gracefully"""
        logger.info("🛑 Stopping bot...")
        self.running = False


async def main():
    # Initialize SDK
    sdk = PacificaSDK(
        private_key=os.getenv("SOLANA_PRIVATE_KEY"),
        base_url=BotConfig.BASE_URL
    )

    # Initialize config
    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL
    )

    # Create bot
    bot = PacificaTradingBot(sdk, config)

    # Setup signal handlers
    def signal_handler(sig, frame):
        bot.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.start()
    finally:
        logger.info("✅ Bot stopped cleanly")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
