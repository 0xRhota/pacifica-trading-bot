#!/usr/bin/env python3
"""
Dry-run version of Pacifica bot - simulates trades without placing real orders
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
import random

from pacifica_bot import PacificaAPI, TradingConfig, Position
from risk_manager import RiskManager
from config import BotConfig

logging.basicConfig(
    level=getattr(logging, BotConfig.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("dry_run.log")
    ]
)

logger = logging.getLogger(__name__)

class DryRunBot:
    """Dry run bot - checks positions every 45s, trades every 15min"""

    def __init__(self, config: TradingConfig, account_address: str):
        self.config = config
        self.account_address = account_address
        self.api = PacificaAPI(config)
        self.risk_manager = RiskManager(BotConfig)
        self.positions = {}
        self.simulated_trades = []
        self.last_trade_time = 0
        self.running = False

    async def start(self):
        """Start the dry run bot"""
        logger.info("🏃 Starting Pacifica Dry Run Bot...")
        logger.info(f"Check frequency: {BotConfig.CHECK_FREQUENCY_SECONDS}s")
        logger.info(f"Trade frequency: {BotConfig.TRADE_FREQUENCY_SECONDS}s ({BotConfig.TRADE_FREQUENCY_SECONDS/60:.1f} minutes)")
        logger.info(f"Position sizes: ${BotConfig.SMALL_TRADE_SIZE-3:.0f}-${BotConfig.MAX_POSITION_SIZE_USD:.0f}")
        logger.info(f"Max leverage: {BotConfig.MAX_LEVERAGE}x")
        logger.info(f"Longs only: {BotConfig.LONGS_ONLY}")

        self.running = True

        async with self.api:
            # Get initial account info
            account = await self.api.get_account_info(self.account_address)
            if account:
                logger.info(f"💰 Account Balance: ${float(account.get('balance', 0)):.2f}")
                logger.info(f"💰 Account Equity: ${float(account.get('account_equity', 0)):.2f}")
                logger.info(f"📊 Active Positions: {account.get('positions_count', 0)}")

            # Main loop
            while self.running:
                try:
                    await self._check_and_manage_positions()
                    await self._maybe_open_new_position()
                    await asyncio.sleep(BotConfig.CHECK_FREQUENCY_SECONDS)
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    await asyncio.sleep(5)

    async def _check_and_manage_positions(self):
        """Check existing positions and close if needed"""
        if not self.positions:
            return

        logger.info(f"🔍 Checking {len(self.positions)} open positions...")

        for symbol, position in list(self.positions.items()):
            try:
                current_price = await self.api.get_market_price(symbol)
                if not current_price:
                    continue

                # Calculate P&L
                if position.side == "buy":
                    pnl_pct = (current_price - position.entry_price) / position.entry_price
                else:
                    pnl_pct = (position.entry_price - current_price) / position.entry_price

                pnl_usd = pnl_pct * (abs(position.size) * position.entry_price)
                time_held = time.time() - position.timestamp

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
                    logger.info(f"🔴 [DRY RUN] Closing {symbol} position: {close_reason}")
                    logger.info(f"   Entry: ${position.entry_price:.2f}, Exit: ${current_price:.2f}")
                    logger.info(f"   P&L: ${pnl_usd:.4f} ({pnl_pct:.4%})")

                    # Record trade
                    self.simulated_trades.append({
                        'symbol': symbol,
                        'side': position.side,
                        'entry_price': position.entry_price,
                        'exit_price': current_price,
                        'size': position.size,
                        'pnl': pnl_usd,
                        'pnl_pct': pnl_pct,
                        'duration': time_held,
                        'reason': close_reason
                    })

                    # Update risk manager
                    self.risk_manager.record_trade_closed(symbol, current_price, pnl_usd)

                    # Remove position
                    del self.positions[symbol]
                else:
                    logger.debug(f"📊 {symbol}: Entry ${position.entry_price:.2f}, Current ${current_price:.2f}, P&L: {pnl_pct:.4%}, Held: {time_held/60:.1f}min")

            except Exception as e:
                logger.error(f"Error checking position {symbol}: {e}")

    async def _maybe_open_new_position(self):
        """Open new position if enough time has passed"""
        time_since_last_trade = time.time() - self.last_trade_time

        if time_since_last_trade < BotConfig.TRADE_FREQUENCY_SECONDS:
            return

        # Check account first
        account = await self.api.get_account_info(self.account_address)
        if not account:
            logger.warning("⚠️  Could not get account info")
            return

        balance = float(account.get('balance', 0))
        equity = float(account.get('account_equity', 0))
        margin_used = float(account.get('total_margin_used', 0))

        # Calculate current leverage
        if equity > 0:
            current_leverage = margin_used / equity
        else:
            current_leverage = 0

        logger.info(f"💰 Balance: ${balance:.2f}, Equity: ${equity:.2f}, Margin Used: ${margin_used:.2f}")
        logger.info(f"📊 Current Leverage: {current_leverage:.2f}x (max: {BotConfig.MAX_LEVERAGE}x)")

        # Don't trade if we're at max leverage
        if current_leverage >= BotConfig.MAX_LEVERAGE:
            logger.warning(f"⚠️  At max leverage ({current_leverage:.2f}x), skipping new trades")
            return

        # Pick a random symbol to trade
        symbol = random.choice(BotConfig.TRADING_SYMBOLS)

        try:
            current_price = await self.api.get_market_price(symbol)
            if not current_price:
                logger.warning(f"⚠️  Could not get price for {symbol}")
                return

            orderbook = await self.api.get_orderbook(symbol)
            if not orderbook or "bids" not in orderbook or "asks" not in orderbook:
                logger.warning(f"⚠️  Could not get orderbook for {symbol}")
                return

            bids = orderbook["bids"]
            asks = orderbook["asks"]

            if not bids or not asks:
                return

            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            spread_pct = (best_ask - best_bid) / best_bid

            # Only trade if spread exists (any spread is fine for dry run)
            if spread_pct < 0.00001:
                logger.info(f"⚠️  Spread too tight for {symbol}: {spread_pct:.4%}")
                return

            # Calculate position size
            position_value = random.uniform(5, min(BotConfig.MAX_POSITION_SIZE_USD, 10))
            size = position_value / current_price

            side = "buy"  # Longs only

            logger.info(f"🟢 [DRY RUN] Opening {side} position for {symbol}")
            logger.info(f"   Price: ${current_price:.2f}, Size: {size:.6f} (${position_value:.2f})")
            logger.info(f"   Spread: {spread_pct:.4%}")

            # Record position
            self.positions[symbol] = Position(
                symbol=symbol,
                size=size if side == "buy" else -size,
                entry_price=current_price,
                side=side,
                timestamp=time.time()
            )

            # Update risk manager
            self.risk_manager.record_trade_opened(symbol, side, size, current_price)

            self.last_trade_time = time.time()

        except Exception as e:
            logger.error(f"Error opening position for {symbol}: {e}")

    async def stop(self):
        """Stop the bot"""
        logger.info("🛑 Stopping bot...")
        self.running = False

        # Print summary
        await self.print_summary()

    async def print_summary(self):
        """Print trading summary"""
        risk_summary = self.risk_manager.get_risk_summary()

        print("\n" + "="*60)
        print(f"DRY RUN SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        print(f"Total Simulated Trades: {len(self.simulated_trades)}")
        print(f"Total Volume:           ${risk_summary['total_volume']:,.2f}")
        print(f"Total P&L:              ${risk_summary['total_pnl']:,.4f}")
        print(f"Win Rate:               {risk_summary['win_rate']:.1%}")
        print(f"Open Positions:         {len(self.positions)}")
        print("="*60)

        if self.simulated_trades:
            print("\nTRADE HISTORY:")
            for i, trade in enumerate(self.simulated_trades[-10:], 1):
                print(f"{i}. {trade['symbol']} {trade['side']}: ${trade['pnl']:.4f} ({trade['pnl_pct']:.4%}) - {trade['reason']}")
        print()

async def main():
    """Main entry point"""
    print("🏃 Starting Pacifica Dry Run Bot")
    print(f"⚠️  DRY RUN MODE - No real trades will be placed")
    print(f"Check interval: {BotConfig.CHECK_FREQUENCY_SECONDS}s")
    print(f"Trade interval: {BotConfig.TRADE_FREQUENCY_SECONDS}s ({BotConfig.TRADE_FREQUENCY_SECONDS/60:.1f} minutes)")
    print()

    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL,
        max_position_size=BotConfig.MAX_POSITION_SIZE_USD,
        min_profit_threshold=BotConfig.MIN_PROFIT_THRESHOLD,
        max_loss_threshold=BotConfig.MAX_LOSS_THRESHOLD,
        trade_frequency=BotConfig.CHECK_FREQUENCY_SECONDS,
        symbols=BotConfig.TRADING_SYMBOLS
    )

    bot = DryRunBot(config, BotConfig.ACCOUNT_ADDRESS)

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
