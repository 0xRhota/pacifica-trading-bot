#!/usr/bin/env python3
"""
Live Trading Bot - Places REAL orders using Pacifica SDK
Checks positions every 45s, opens new positions every 15min
"""

import asyncio
import logging
import signal
import sys
import time
import os
import math
from datetime import datetime
from dotenv import load_dotenv

from pacifica_bot import PacificaAPI, TradingConfig
from pacifica_sdk import PacificaSDK
from risk_manager import RiskManager
from trade_tracker import tracker
from config import BotConfig

# Load environment
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("live_trading.log")
    ]
)

logger = logging.getLogger(__name__)

class LiveTradingBot:
    """Live trading bot with SDK integration"""

    def __init__(self, sdk: PacificaSDK, config: TradingConfig):
        self.sdk = sdk
        self.config = config
        self.api = PacificaAPI(config)
        self.risk_manager = RiskManager(BotConfig)
        self.open_positions = {}  # symbol -> order_id
        self.last_trade_time = 0
        self.running = False

    async def start(self):
        """Start live trading"""
        logger.info("🔴 STARTING LIVE TRADING BOT")
        logger.info(f"⚠️  THIS WILL PLACE REAL ORDERS WITH REAL MONEY")
        logger.info(f"Check frequency: {BotConfig.CHECK_FREQUENCY_SECONDS}s")
        logger.info(f"Trade frequency: {BotConfig.TRADE_FREQUENCY_SECONDS}s ({BotConfig.TRADE_FREQUENCY_SECONDS/60:.0f} min)")
        logger.info(f"Position sizes: ${BotConfig.MIN_POSITION_SIZE_USD}-${BotConfig.MAX_POSITION_SIZE_USD}")
        logger.info(f"Max leverage: {BotConfig.MAX_LEVERAGE}x")
        logger.info(f"Longs only: {BotConfig.LONGS_ONLY}")

        self.running = True

        async with self.api:
            # Get account info
            account = await self.api.get_account_info(BotConfig.ACCOUNT_ADDRESS)
            if account:
                logger.info(f"💰 Balance: ${float(account.get('balance', 0)):.2f}")
                logger.info(f"💰 Equity: ${float(account.get('account_equity', 0)):.2f}")

            # Load existing positions from API on startup
            await self._sync_positions_from_api()

            # Main loop
            while self.running:
                try:
                    await self._check_and_manage_positions()
                    await self._maybe_open_new_position()
                    await asyncio.sleep(BotConfig.CHECK_FREQUENCY_SECONDS)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}", exc_info=True)
                    await asyncio.sleep(5)

    async def _sync_positions_from_api(self):
        """Sync local position tracking with actual API positions"""
        result = self.sdk.get_positions()
        if not result.get('success'):
            logger.error("Failed to get positions from API")
            return

        api_positions = result.get('data', [])

        if api_positions:
            logger.info(f"📊 Found {len(api_positions)} existing positions in API")
            for pos in api_positions:
                symbol = pos.get('symbol')
                # We don't have order_id from positions endpoint, so we can't track these
                # Log them but don't add to tracking
                logger.info(f"   {symbol}: {pos.get('side')} {pos.get('amount')} @ ${pos.get('entry_price')}")
                logger.warning(f"   ⚠️  Position opened outside bot - cannot auto-manage")
        else:
            logger.info("✅ No existing positions - clean start")

    async def _check_and_manage_positions(self):
        """Check positions and close if needed"""
        # First, sync with API to detect externally closed positions
        result = self.sdk.get_positions()
        if result.get('success'):
            api_positions = result.get('data', [])
            api_symbols = set(p.get('symbol') for p in api_positions)

            # Remove positions from tracking if they were closed externally
            for symbol in list(self.open_positions.keys()):
                if symbol not in api_symbols:
                    order_id = self.open_positions[symbol]
                    logger.warning(f"⚠️  {symbol} position #{order_id} closed externally - removing from tracking")
                    del self.open_positions[symbol]

        if not self.open_positions:
            return

        logger.info(f"🔍 Checking {len(self.open_positions)} positions...")

        for symbol, order_id in list(self.open_positions.items()):
            try:
                # Get current price
                current_price = await self.api.get_market_price(symbol)
                if not current_price:
                    continue

                # Find trade in tracker
                open_trades = tracker.get_open_trades()
                trade = None
                for t in open_trades:
                    if t.get('order_id') == str(order_id):
                        trade = t
                        break

                if not trade:
                    logger.warning(f"Trade {order_id} not found in tracker")
                    continue

                entry_price = trade['entry_price']
                size = trade['size']
                side = trade['side']
                time_held = time.time() - datetime.fromisoformat(trade['timestamp']).timestamp()

                # Calculate P&L
                if side == "buy":
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - current_price) / entry_price

                # Check if should close
                should_close = False
                close_reason = ""

                if pnl_pct >= BotConfig.MIN_PROFIT_THRESHOLD:
                    should_close = True
                    close_reason = f"Take profit: {pnl_pct:.4%}"
                elif pnl_pct <= -BotConfig.MAX_LOSS_THRESHOLD:
                    should_close = True
                    close_reason = f"Stop loss: {pnl_pct:.4%}"
                elif time_held > BotConfig.MAX_POSITION_HOLD_TIME:
                    should_close = True
                    close_reason = f"Time limit: {time_held/60:.1f}min"

                if should_close:
                    await self._close_position(symbol, order_id, current_price, close_reason)

            except Exception as e:
                logger.error(f"Error checking {symbol}: {e}", exc_info=True)

    async def _maybe_open_new_position(self):
        """Open new position if conditions met"""
        time_since_last = time.time() - self.last_trade_time

        if time_since_last < BotConfig.TRADE_FREQUENCY_SECONDS:
            return

        # Get account info
        account = await self.api.get_account_info(BotConfig.ACCOUNT_ADDRESS)
        if not account:
            logger.warning("Could not get account info")
            return

        balance = float(account.get('balance', 0))
        equity = float(account.get('account_equity', 0))
        margin_used = float(account.get('total_margin_used', 0))

        # Check leverage
        current_leverage = margin_used / equity if equity > 0 else 0

        logger.info(f"💰 Balance: ${balance:.2f}, Equity: ${equity:.2f}, Leverage: {current_leverage:.2f}x")

        if current_leverage >= BotConfig.MAX_LEVERAGE:
            logger.warning(f"At max leverage ({current_leverage:.2f}x), skipping")
            return

        # Choose symbol
        import random
        symbol = random.choice(BotConfig.TRADING_SYMBOLS)

        try:
            # Get price
            current_price = await self.api.get_market_price(symbol)
            if not current_price:
                return

            # Get orderbook
            orderbook = await self.api.get_orderbook(symbol)
            if not orderbook or "bids" not in orderbook:
                return

            # Calculate position size (round up to meet $10 minimum)
            position_value = random.uniform(BotConfig.MIN_POSITION_SIZE_USD, BotConfig.MAX_POSITION_SIZE_USD)
            size = position_value / current_price
            size = math.ceil(size / BotConfig.LOT_SIZE) * BotConfig.LOT_SIZE
            actual_value = size * current_price

            # Verify meets minimum
            if actual_value < 10:
                logger.warning(f"Position too small: ${actual_value:.2f} < $10")
                return

            # SAFETY CHECK: Verify actual value is within expected range
            if actual_value > BotConfig.MAX_POSITION_SIZE_USD * 2:
                logger.error(f"❌ Position too large: ${actual_value:.2f} > ${BotConfig.MAX_POSITION_SIZE_USD * 2:.2f}")
                return

            side = "bid"  # Longs only

            logger.info(f"🟢 Opening {side} position for {symbol}")
            logger.info(f"   Price: ${current_price:.2f}, Size: {size:.6f}, Value: ${actual_value:.2f}")

            # Place order via SDK
            result = self.sdk.create_market_order(
                symbol=symbol,
                side=side,
                amount=f"{size:.6f}",
                slippage_percent="1.0"
            )

            if result.get('success'):
                order_id = result['data'].get('order_id')
                logger.info(f"✅ Order placed: #{order_id}")

                # Track position
                self.open_positions[symbol] = order_id

                # Log to tracker
                tracker.log_entry(
                    order_id=str(order_id),
                    symbol=symbol,
                    side="buy",
                    size=size,
                    entry_price=current_price,
                    notes=f"Live bot - {side} order"
                )

                # Update risk manager
                self.risk_manager.record_trade_opened(symbol, "buy", size, current_price)

                self.last_trade_time = time.time()
            else:
                logger.error(f"❌ Order failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error opening position: {e}", exc_info=True)

    async def _close_position(self, symbol: str, entry_order_id: str, current_price: float, reason: str):
        """Close position"""
        logger.info(f"🔴 Closing {symbol} position: {reason}")

        try:
            # Get trade details
            open_trades = tracker.get_open_trades()
            trade = None
            for t in open_trades:
                if t.get('order_id') == str(entry_order_id):
                    trade = t
                    break

            if not trade:
                logger.error(f"Trade {entry_order_id} not found")
                return

            size = trade['size']
            entry_price = trade['entry_price']

            # Place closing order
            close_side = "ask" if trade['side'] == "buy" else "bid"

            result = self.sdk.create_market_order(
                symbol=symbol,
                side=close_side,
                amount=f"{size:.6f}",
                slippage_percent="1.0"
            )

            if result.get('success'):
                # Calculate P&L
                if trade['side'] == "buy":
                    pnl = (current_price - entry_price) * size
                else:
                    pnl = (entry_price - current_price) * size

                actual_value = size * current_price
                fees = actual_value * 0.001  # 0.1% estimate
                pnl_net = pnl - fees

                logger.info(f"✅ Position closed. P&L: ${pnl_net:.4f}")

                # Log exit
                tracker.log_exit(
                    order_id=str(entry_order_id),
                    exit_price=current_price,
                    exit_reason=reason,
                    fees=fees
                )

                # Update risk manager
                self.risk_manager.record_trade_closed(symbol, current_price, pnl_net)

                # Remove from open positions
                del self.open_positions[symbol]

                # Print stats
                stats = tracker.get_stats()
                logger.info(f"📊 Win Rate: {stats['win_rate']:.1%}, Total P&L: ${stats['total_pnl']:.4f}")

            else:
                logger.error(f"❌ Close order failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error closing position: {e}", exc_info=True)

    async def stop(self):
        """Stop bot"""
        logger.info("🛑 Stopping bot...")
        self.running = False

        # Close all positions
        for symbol, order_id in list(self.open_positions.items()):
            try:
                price = await self.api.get_market_price(symbol)
                if price:
                    await self._close_position(symbol, order_id, price, "Bot shutdown")
            except:
                pass

        # Print final stats
        tracker.print_stats()

async def main():
    """Main entry point"""
    print("="*60)
    print("⚠️  LIVE TRADING BOT")
    print("="*60)
    print("This will place REAL orders with REAL money!")
    print(f"Position sizes: ${BotConfig.MIN_POSITION_SIZE_USD}-${BotConfig.MAX_POSITION_SIZE_USD}")
    print(f"Check every: {BotConfig.CHECK_FREQUENCY_SECONDS}s")
    print(f"Trade every: {BotConfig.TRADE_FREQUENCY_SECONDS/60:.0f} minutes")
    print("="*60)
    print()

    # Get private key
    private_key = os.getenv("SOLANA_PRIVATE_KEY")
    if not private_key:
        print("❌ SOLANA_PRIVATE_KEY not found in .env")
        return

    # Initialize SDK
    sdk = PacificaSDK(private_key, BotConfig.BASE_URL)
    logger.info(f"✅ SDK initialized: {sdk.get_account_address()}")

    # Create config
    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL,
        symbols=BotConfig.TRADING_SYMBOLS
    )

    # Create bot
    bot = LiveTradingBot(sdk, config)

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

if __name__ == "__main__":
    asyncio.run(main())
