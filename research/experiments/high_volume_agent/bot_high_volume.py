#!/usr/bin/env python3
"""
High Volume Trading Bot - Runs on Hibachi AND Extended
Based on Qwen analysis 2025-11-27

KEY DIFFERENCES FROM SWING TRADING:
- 4:1 R/R (4% TP, 1% SL) vs 3:1 (15% TP, 5% SL)
- TIME EXIT: Close after 1 hour (the secret to high volume)
- 10-minute check intervals (vs 30-minute)
- 20 trades/day max (caps fees at ~3%)
- Target: +3% daily profit at 25% win rate

Usage:
    python -m high_volume_agent.bot_high_volume --dry-run
    python -m high_volume_agent.bot_high_volume --live
    python -m high_volume_agent.bot_high_volume --live --hibachi-only
    python -m high_volume_agent.bot_high_volume --live --extended-only
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports
from llm_agent.llm import LLMTradingAgent
from trade_tracker import TradeTracker

# DEX imports
from dexes.hibachi import HibachiSDK
from hibachi_agent.execution.hibachi_executor import HibachiTradeExecutor
from hibachi_agent.data.hibachi_aggregator import HibachiMarketDataAggregator

from extended_agent.execution.extended_executor import create_extended_executor_from_env
from extended_agent.data.extended_aggregator import ExtendedMarketDataAggregator

# High volume specific
from high_volume_agent.config import (
    STRATEGY_FILE,
    TAKE_PROFIT_PCT,
    STOP_LOSS_PCT,
    TIME_EXIT_MINUTES,
    MIN_HOLD_MINUTES,
    CHECK_INTERVAL_SECONDS,
    MAX_TRADES_PER_DAY,
    MAX_DAILY_LOSS_PCT,
    MAX_POSITIONS,
    LOG_FILE
)
from high_volume_agent.high_volume_exit_rules import HighVolumeExitRules, DailyTracker

# Load environment variables
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(project_root, '.env'), override=True)

# Configure logging
os.makedirs(os.path.join(project_root, 'logs'), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(project_root, LOG_FILE)),
        logging.StreamHandler()
    ]
)

# Suppress noisy loggers
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)
logging.getLogger('aiohttp').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class HighVolumeTradingBot:
    """
    High Volume Trading Bot

    Based on Qwen analysis:
    - 4:1 R/R (4% TP, 1% SL) = only needs 22% win rate
    - Time-based exits (1 hour) = maintains high volume
    - 10-20 trades/day = optimal fee/profit balance
    """

    def __init__(
        self,
        dry_run: bool = True,
        hibachi_enabled: bool = True,
        extended_enabled: bool = True,
        model: str = "deepseek-chat"
    ):
        self.dry_run = dry_run
        self.hibachi_enabled = hibachi_enabled
        self.extended_enabled = extended_enabled

        logger.info("=" * 80)
        logger.info("HIGH VOLUME TRADING BOT INITIALIZATION")
        logger.info("=" * 80)
        logger.info(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
        logger.info(f"Strategy: v6_high_volume (4:1 R/R)")
        logger.info(f"Take Profit: +{TAKE_PROFIT_PCT}%")
        logger.info(f"Stop Loss: -{STOP_LOSS_PCT}%")
        logger.info(f"Time Exit: {TIME_EXIT_MINUTES} minutes")
        logger.info(f"Max Trades/Day: {MAX_TRADES_PER_DAY}")
        logger.info(f"Check Interval: {CHECK_INTERVAL_SECONDS}s")

        # Initialize exit rules
        self.exit_rules = HighVolumeExitRules(
            take_profit_pct=TAKE_PROFIT_PCT,
            stop_loss_pct=STOP_LOSS_PCT,
            time_exit_minutes=TIME_EXIT_MINUTES,
            min_hold_minutes=MIN_HOLD_MINUTES
        )

        # Daily tracker for trade limits
        self.daily_tracker = DailyTracker(
            max_trades=MAX_TRADES_PER_DAY,
            max_loss_pct=MAX_DAILY_LOSS_PCT
        )

        # Get API keys
        cambrian_api_key = os.getenv('CAMBRIAN_API_KEY')
        deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        openrouter_api_key = os.getenv('OPEN_ROUTER')

        # Select LLM
        if model == 'qwen-max':
            llm_api_key = openrouter_api_key
            logger.info(f"LLM: Qwen-Max via OpenRouter")
        else:
            llm_api_key = deepseek_api_key
            logger.info(f"LLM: DeepSeek-Chat")

        # Initialize LLM agent with high volume strategy
        strategy_path = os.path.join(project_root, STRATEGY_FILE)
        self.llm_agent = LLMTradingAgent(
            deepseek_api_key=llm_api_key,
            cambrian_api_key=cambrian_api_key,
            model=model,
            max_retries=2,
            daily_spend_limit=10.0,
            max_positions=MAX_POSITIONS,
            strategy_file=strategy_path
        )
        logger.info(f"Strategy loaded from: {STRATEGY_FILE}")

        # Initialize DEXs
        if hibachi_enabled:
            self._init_hibachi(cambrian_api_key)

        if extended_enabled:
            self._init_extended(cambrian_api_key)

        logger.info("=" * 80)
        logger.info("INITIALIZATION COMPLETE")
        logger.info("=" * 80)

    def _init_hibachi(self, cambrian_api_key: str):
        """Initialize Hibachi DEX"""
        hibachi_api_key = os.getenv('HIBACHI_PUBLIC_KEY')
        hibachi_api_secret = os.getenv('HIBACHI_PRIVATE_KEY')
        hibachi_account_id = os.getenv('HIBACHI_ACCOUNT_ID')

        if not all([hibachi_api_key, hibachi_api_secret, hibachi_account_id]):
            logger.warning("Hibachi credentials missing - disabling")
            self.hibachi_enabled = False
            return

        self.hibachi_sdk = HibachiSDK(
            api_key=hibachi_api_key,
            api_secret=hibachi_api_secret,
            account_id=hibachi_account_id
        )

        self.hibachi_aggregator = HibachiMarketDataAggregator(
            cambrian_api_key=cambrian_api_key,
            sdk=self.hibachi_sdk,
            interval="15m",  # Use 15m candles, check every 10 min
            candle_limit=100
        )

        self.hibachi_tracker = TradeTracker(dex="hibachi_highvol")

        self.hibachi_executor = HibachiTradeExecutor(
            hibachi_sdk=self.hibachi_sdk,
            trade_tracker=self.hibachi_tracker,
            dry_run=self.dry_run,
            default_position_size=10.0,
            max_positions=MAX_POSITIONS,
            max_position_age_minutes=TIME_EXIT_MINUTES
        )

        # Initialize symbols
        asyncio.get_event_loop().run_until_complete(
            self.hibachi_aggregator.hibachi._initialize_symbols()
        )

        logger.info("Hibachi DEX initialized")

    def _init_extended(self, cambrian_api_key: str):
        """Initialize Extended DEX"""
        self.extended_tracker = TradeTracker(dex="extended_highvol")

        self.extended_executor = create_extended_executor_from_env(
            trade_tracker=self.extended_tracker,
            dry_run=self.dry_run
        )

        if not self.extended_executor:
            logger.warning("Extended executor failed - disabling")
            self.extended_enabled = False
            return

        self.extended_executor.max_positions = MAX_POSITIONS
        self.extended_executor.max_position_age_minutes = TIME_EXIT_MINUTES

        self.extended_aggregator = ExtendedMarketDataAggregator(
            cambrian_api_key=cambrian_api_key,
            sdk=None,
            interval="15m",
            candle_limit=100
        )

        logger.info("Extended DEX initialized")

    async def _run_dex_cycle(
        self,
        dex_name: str,
        aggregator,
        executor,
        tracker: TradeTracker
    ) -> Dict:
        """Run single cycle for a DEX"""
        logger.info(f"--- {dex_name} Cycle ---")

        # Check daily limits
        can_trade, reason = self.daily_tracker.can_trade()
        if not can_trade:
            logger.warning(f"  {reason}")
            return {"success": True, "skipped": True, "reason": reason}

        try:
            # Fetch market data
            market_data_dict = await aggregator.fetch_all_markets()
            if not market_data_dict:
                logger.warning(f"  No market data")
                return {"success": False, "error": "No market data"}

            logger.info(f"  Markets: {len(market_data_dict)}")

            # Fetch positions
            raw_positions = await executor._fetch_open_positions()
            open_positions = []

            for pos in raw_positions:
                symbol = pos.get('symbol')
                size = float(pos.get('quantity', pos.get('size', 0)))
                if size == 0:
                    continue

                direction = pos.get('direction', pos.get('side', 'Long'))
                side = 'LONG' if direction in ['Long', 'LONG'] else 'SHORT'

                tracker_data = tracker.get_open_trade_for_symbol(symbol)
                entry_price = tracker_data.get('entry_price', 0) if tracker_data else 0

                if dex_name == "Hibachi":
                    current_price = await self.hibachi_sdk.get_price(symbol)
                else:
                    current_price = pos.get('mark_price', entry_price)

                if not current_price:
                    current_price = entry_price

                # Calculate PnL
                if entry_price and entry_price > 0:
                    if side == 'LONG':
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    else:
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                else:
                    pnl_pct = 0

                open_positions.append({
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'size': size,
                    'pnl_pct': pnl_pct / 100
                })

            logger.info(f"  Positions: {len(open_positions)}")

            # Check exit rules for each position (includes TIME EXIT)
            forced_exits = []
            for pos in open_positions:
                symbol = pos['symbol']
                tracker_data = tracker.get_open_trade_for_symbol(symbol)
                market_data = market_data_dict.get(symbol, {})

                should_close, reason = self.exit_rules.check_should_force_close(
                    pos, market_data, tracker_data
                )

                if should_close:
                    logger.info(f"  EXIT: {symbol} - {reason}")

                    result = await executor.execute_decision({
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'reasoning': f"HIGH VOL RULE: {reason}"
                    })

                    if result.get('success'):
                        # Record in daily tracker
                        pnl = pos['pnl_pct'] * 100
                        self.daily_tracker.record_trade(pnl)

                    forced_exits.append((symbol, reason, result.get('success')))
                    open_positions = [p for p in open_positions if p['symbol'] != symbol]

            if forced_exits:
                logger.info(f"  Forced exits: {len(forced_exits)}")

            # Skip LLM if max positions OR can't trade
            can_trade, reason = self.daily_tracker.can_trade()
            if len(open_positions) >= MAX_POSITIONS:
                logger.info(f"  Max positions ({MAX_POSITIONS}) reached")
                return {"success": True, "positions": len(open_positions), "new_trades": 0}

            if not can_trade:
                logger.info(f"  {reason}")
                return {"success": True, "positions": len(open_positions), "new_trades": 0}

            # Format prompt for LLM
            market_table = aggregator.format_market_table(market_data_dict)
            account_balance = await executor._fetch_account_balance() or 0
            recently_closed = tracker.get_recently_closed_symbols(hours=1)  # 1 hour cooldown

            prompt = self.llm_agent.prompt_formatter.format_trading_prompt(
                market_table=market_table,
                open_positions=open_positions,
                account_balance=account_balance,
                recently_closed_symbols=recently_closed,
                dex_name=dex_name,
                analyzed_tokens=list(market_data_dict.keys())
            )

            # Query LLM
            logger.info(f"  Querying LLM...")
            result = self.llm_agent.model_client.query(
                prompt=prompt,
                max_tokens=500,
                temperature=0.1
            )

            if not result:
                logger.warning(f"  LLM query failed")
                return {"success": False, "error": "LLM failed"}

            # Parse decisions
            parsed_decisions = self.llm_agent.response_parser.parse_multiple_decisions(
                result["content"]
            )

            if not parsed_decisions:
                logger.info(f"  No decisions from LLM")
                return {"success": True, "positions": len(open_positions), "new_trades": 0}

            # Execute decisions
            new_trades = 0
            for parsed in parsed_decisions:
                # Check daily limit before each trade
                can_trade, reason = self.daily_tracker.can_trade()
                if not can_trade:
                    logger.info(f"  {reason} - stopping entries")
                    break

                symbol = parsed.get('symbol')
                action = parsed.get('action', '').upper()
                confidence = parsed.get('confidence', 0.5)

                # Only trade high confidence
                if confidence < 0.6:
                    logger.debug(f"  Skipping {symbol}: confidence {confidence:.2f} < 0.6")
                    continue

                # Normalize symbol
                if dex_name == "Hibachi" and not symbol.endswith("/USDT-P"):
                    symbol = f"{symbol}/USDT-P"
                elif dex_name == "Extended" and not symbol.endswith("-USD"):
                    symbol = f"{symbol}-USD"

                # Check if already have position
                has_position = any(p['symbol'] == symbol for p in open_positions)
                if has_position and action in ['BUY', 'SELL']:
                    continue

                # Check max positions
                if len(open_positions) + new_trades >= MAX_POSITIONS:
                    break

                # Map actions
                if action == "BUY":
                    action = "LONG"
                elif action == "SELL":
                    action = "SHORT"

                # Execute
                decision = {
                    'action': action,
                    'symbol': symbol,
                    'reasoning': parsed.get('reason', ''),
                    'confidence': confidence
                }

                logger.info(f"  Executing: {action} {symbol} (conf: {confidence:.2f})")
                exec_result = await executor.execute_decision(decision)

                if exec_result.get('success'):
                    new_trades += 1
                    logger.info(f"    Success")
                else:
                    logger.warning(f"    Failed: {exec_result.get('error')}")

            return {
                "success": True,
                "positions": len(open_positions) + new_trades,
                "new_trades": new_trades,
                "forced_exits": len(forced_exits)
            }

        except Exception as e:
            logger.error(f"  Error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def run_once(self):
        """Run single cycle on all DEXs"""
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"HIGH VOLUME CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Show daily status
        status = self.daily_tracker.get_status()
        logger.info(f"Daily: {status['trades_today']}/{MAX_TRADES_PER_DAY} trades, {status['daily_pnl_pct']:+.2f}% P/L")
        logger.info("=" * 80)

        results = {}

        if self.hibachi_enabled:
            results['hibachi'] = await self._run_dex_cycle(
                "Hibachi",
                self.hibachi_aggregator,
                self.hibachi_executor,
                self.hibachi_tracker
            )

        if self.extended_enabled:
            results['extended'] = await self._run_dex_cycle(
                "Extended",
                self.extended_aggregator,
                self.extended_executor,
                self.extended_tracker
            )

        # Summary
        logger.info("")
        logger.info("--- Cycle Summary ---")
        for dex, result in results.items():
            if result.get('skipped'):
                logger.info(f"  {dex}: SKIPPED - {result.get('reason')}")
            elif result.get('success'):
                logger.info(f"  {dex}: {result.get('positions', 0)} positions, {result.get('new_trades', 0)} new, {result.get('forced_exits', 0)} exits")
            else:
                logger.warning(f"  {dex}: FAILED - {result.get('error')}")

        return results

    async def run(self):
        """Run continuous trading loop"""
        logger.info("Starting High Volume Trading Bot...")
        cycle_count = 0

        try:
            while True:
                cycle_count += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"Cycle {cycle_count}")
                logger.info(f"{'='*80}")

                await self.run_once()

                logger.info(f"Next cycle in {CHECK_INTERVAL_SECONDS}s ({CHECK_INTERVAL_SECONDS//60}min)...")
                await asyncio.sleep(CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("\nShutting down...")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="High Volume Trading Bot")
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--live', action='store_true', help='Live trading')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--hibachi-only', action='store_true', help='Hibachi only')
    parser.add_argument('--extended-only', action='store_true', help='Extended only')
    parser.add_argument('--model', type=str, default='deepseek-chat',
                        choices=['deepseek-chat', 'qwen-max'])

    args = parser.parse_args()

    if not args.dry_run and not args.live:
        logger.error("Must specify --dry-run or --live")
        sys.exit(1)

    bot = HighVolumeTradingBot(
        dry_run=not args.live,
        hibachi_enabled=not args.extended_only,
        extended_enabled=not args.hibachi_only,
        model=args.model
    )

    if args.once:
        asyncio.run(bot.run_once())
    else:
        asyncio.run(bot.run())


if __name__ == "__main__":
    main()
