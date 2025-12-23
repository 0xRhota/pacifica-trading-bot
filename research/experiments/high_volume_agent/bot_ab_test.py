#!/usr/bin/env python3
"""
A/B Test Bot - Runs TWO strategies simultaneously on different DEXs

STRATEGY A (Hibachi): TIME_CAPPED
- 4% TP, 1% SL, 1 HOUR MAX HOLD
- High turnover, many trades

STRATEGY B (Extended): RUNNERS_RUN
- 8% TP, 1% SL, NO TIME LIMIT
- Trailing stop at +2%, let winners run

This allows direct comparison of:
- Time-capped exits vs letting runners run
- Fixed TP vs trailing stops
- High volume vs higher R/R

Usage:
    python -m high_volume_agent.bot_ab_test --dry-run
    python -m high_volume_agent.bot_ab_test --live
"""

import os
import sys
import asyncio
import logging
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Any
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

# Strategy imports
from high_volume_agent.strategies import (
    STRATEGY_A_TIME_CAPPED,
    STRATEGY_B_RUNNERS_RUN,
    StrategyConfig,
    print_strategy_comparison
)
from high_volume_agent.adaptive_exit_rules import AdaptiveExitRules

# Load environment variables
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(project_root, '.env'), override=True)

# Configure logging
os.makedirs(os.path.join(project_root, 'logs'), exist_ok=True)
LOG_FILE = 'logs/ab_test_bot.log'
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


class ABTestBot:
    """
    A/B Test Bot - Runs two strategies on different DEXs

    Hibachi: Strategy A (TIME_CAPPED) - 4% TP, 1% SL, 1hr max
    Extended: Strategy B (RUNNERS_RUN) - 8% TP, 1% SL, trailing stops
    """

    def __init__(
        self,
        dry_run: bool = True,
        model: str = "deepseek-chat"
    ):
        self.dry_run = dry_run
        self.model = model
        self.running = False

        # Initialize strategies
        self.strategy_a = STRATEGY_A_TIME_CAPPED
        self.strategy_b = STRATEGY_B_RUNNERS_RUN

        # Exit rules for each DEX
        self.hibachi_exit_rules = AdaptiveExitRules(self.strategy_a)
        self.extended_exit_rules = AdaptiveExitRules(self.strategy_b)

        # Performance tracking
        self.performance = {
            'hibachi': {'trades': 0, 'wins': 0, 'pnl': 0.0, 'start_balance': 0.0},
            'extended': {'trades': 0, 'wins': 0, 'pnl': 0.0, 'start_balance': 0.0}
        }

        # LLM Agent (shared)
        self.llm_agent: Optional[LLMTradingAgent] = None

        # DEX Executors
        self.hibachi_executor: Optional[HibachiTradeExecutor] = None
        self.extended_executor = None

        # Market data aggregators
        self.hibachi_aggregator: Optional[HibachiMarketDataAggregator] = None
        self.extended_aggregator: Optional[ExtendedMarketDataAggregator] = None

        # Trade tracker
        self.trade_tracker = TradeTracker()

        logger.info("=" * 70)
        logger.info("A/B TEST BOT INITIALIZED")
        logger.info("=" * 70)
        print_strategy_comparison()

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing A/B Test Bot...")

        # Load strategy prompt
        strategy_file = os.path.join(project_root, 'llm_agent/prompts_archive/v6_high_volume.txt')
        if os.path.exists(strategy_file):
            with open(strategy_file, 'r') as f:
                strategy_prompt = f.read()
            logger.info(f"Loaded strategy: v6_high_volume")
        else:
            strategy_prompt = None
            logger.warning("No strategy file found, using default prompts")

        # Initialize LLM agent
        self.llm_agent = LLMTradingAgent(
            model=self.model,
            strategy_prompt=strategy_prompt
        )

        # Initialize Hibachi
        try:
            self.hibachi_aggregator = HibachiMarketDataAggregator()
            hibachi_sdk = HibachiSDK.create_from_env()
            self.hibachi_executor = HibachiTradeExecutor(hibachi_sdk, dry_run=self.dry_run)
            logger.info("[HIBACHI] Initialized - Strategy A: TIME_CAPPED")
        except Exception as e:
            logger.error(f"[HIBACHI] Init failed: {e}")

        # Initialize Extended
        try:
            self.extended_aggregator = ExtendedMarketDataAggregator()
            self.extended_executor = create_extended_executor_from_env(dry_run=self.dry_run)
            logger.info("[EXTENDED] Initialized - Strategy B: RUNNERS_RUN")
        except Exception as e:
            logger.error(f"[EXTENDED] Init failed: {e}")

        # Get starting balances
        await self._get_starting_balances()

    async def _get_starting_balances(self):
        """Get starting balances for tracking"""
        try:
            if self.hibachi_executor:
                balance = await self.hibachi_executor.get_balance()
                self.performance['hibachi']['start_balance'] = balance.get('total', 0)
                logger.info(f"[HIBACHI] Starting balance: ${balance.get('total', 0):.2f}")
        except Exception as e:
            logger.error(f"[HIBACHI] Balance fetch failed: {e}")

        try:
            if self.extended_executor:
                balance = await self.extended_executor.get_balance()
                self.performance['extended']['start_balance'] = balance.get('total', 0)
                logger.info(f"[EXTENDED] Starting balance: ${balance.get('total', 0):.2f}")
        except Exception as e:
            logger.error(f"[EXTENDED] Balance fetch failed: {e}")

    async def _get_hibachi_market_data(self, symbol: str) -> Optional[Dict]:
        """Get market data for Hibachi"""
        if not self.hibachi_aggregator:
            return None
        try:
            return await self.hibachi_aggregator.get_aggregated_data(symbol)
        except Exception as e:
            logger.error(f"[HIBACHI] Market data error for {symbol}: {e}")
            return None

    async def _get_extended_market_data(self, symbol: str) -> Optional[Dict]:
        """Get market data for Extended"""
        if not self.extended_aggregator:
            return None
        try:
            return await self.extended_aggregator.get_aggregated_data(symbol)
        except Exception as e:
            logger.error(f"[EXTENDED] Market data error for {symbol}: {e}")
            return None

    async def _check_hibachi_positions(self) -> List[Dict]:
        """Check and manage Hibachi positions with Strategy A (TIME_CAPPED)"""
        if not self.hibachi_executor:
            return []

        positions = await self.hibachi_executor.get_positions()
        for pos in positions:
            symbol = pos['symbol']
            current_price = pos.get('mark_price', pos.get('current_price', 0))

            # Get indicators for trend reversal check
            market_data = await self._get_hibachi_market_data(symbol)
            sma20 = market_data.get('sma20') if market_data else None
            sma50 = market_data.get('sma50') if market_data else None
            macd = market_data.get('macd') if market_data else None

            # Check exit rules
            should_close, reason = self.hibachi_exit_rules.check_should_force_close(
                symbol, current_price, sma20, sma50, macd
            )

            if should_close:
                logger.info(f"[HIBACHI] FORCE CLOSE {symbol}: {reason}")
                if not self.dry_run:
                    try:
                        await self.hibachi_executor.close_position(symbol)
                        self._record_trade('hibachi', symbol, reason)
                    except Exception as e:
                        logger.error(f"[HIBACHI] Close failed: {e}")
                else:
                    logger.info(f"[HIBACHI] DRY RUN - Would close {symbol}")

            else:
                # Log position status
                status = self.hibachi_exit_rules.get_position_status(symbol, current_price)
                logger.debug(f"[HIBACHI] {symbol}: P/L {status['pnl_pct']:+.2f}%, Hold: {status['hold_time']}")

        return positions

    async def _check_extended_positions(self) -> List[Dict]:
        """Check and manage Extended positions with Strategy B (RUNNERS_RUN)"""
        if not self.extended_executor:
            return []

        positions = await self.extended_executor.get_positions()
        for pos in positions:
            symbol = pos['symbol']
            current_price = pos.get('mark_price', pos.get('current_price', 0))

            # Get indicators for trend reversal check
            market_data = await self._get_extended_market_data(symbol)
            sma20 = market_data.get('sma20') if market_data else None
            sma50 = market_data.get('sma50') if market_data else None
            macd = market_data.get('macd') if market_data else None

            # Check exit rules
            should_close, reason = self.extended_exit_rules.check_should_force_close(
                symbol, current_price, sma20, sma50, macd
            )

            if should_close:
                logger.info(f"[EXTENDED] FORCE CLOSE {symbol}: {reason}")
                if not self.dry_run:
                    try:
                        await self.extended_executor.close_position(symbol)
                        self._record_trade('extended', symbol, reason)
                    except Exception as e:
                        logger.error(f"[EXTENDED] Close failed: {e}")
                else:
                    logger.info(f"[EXTENDED] DRY RUN - Would close {symbol}")

            else:
                # Log position status with trailing info
                status = self.extended_exit_rules.get_position_status(symbol, current_price)
                trail_info = " [TRAILING ACTIVE]" if status.get('trailing_active') else ""
                logger.debug(f"[EXTENDED] {symbol}: P/L {status['pnl_pct']:+.2f}%, Peak: +{status['peak_pnl_pct']:.2f}%{trail_info}")

        return positions

    def _record_trade(self, dex: str, symbol: str, reason: str):
        """Record trade result for performance tracking"""
        self.performance[dex]['trades'] += 1
        if 'TAKE PROFIT' in reason or 'TRAILING STOP' in reason:
            self.performance[dex]['wins'] += 1

    async def _make_hibachi_decision(self, market_data: Dict, positions: List) -> Optional[Dict]:
        """Get LLM decision for Hibachi (Strategy A)"""
        # Check if can trade
        can_trade, reason = self.hibachi_exit_rules.can_open_new_trade()
        if not can_trade:
            logger.info(f"[HIBACHI] {reason}")
            return None

        # Check max positions
        if len(positions) >= 3:
            logger.info("[HIBACHI] Max positions (3) reached")
            return None

        # Get LLM decision
        decision = await self.llm_agent.get_trading_decision(
            market_data=market_data,
            current_positions=positions,
            dex_name="HIBACHI"
        )

        return decision

    async def _make_extended_decision(self, market_data: Dict, positions: List) -> Optional[Dict]:
        """Get LLM decision for Extended (Strategy B)"""
        # Check if can trade
        can_trade, reason = self.extended_exit_rules.can_open_new_trade()
        if not can_trade:
            logger.info(f"[EXTENDED] {reason}")
            return None

        # Check max positions
        if len(positions) >= 3:
            logger.info("[EXTENDED] Max positions (3) reached")
            return None

        # Get LLM decision
        decision = await self.llm_agent.get_trading_decision(
            market_data=market_data,
            current_positions=positions,
            dex_name="EXTENDED"
        )

        return decision

    async def _execute_hibachi_trade(self, decision: Dict, current_price: float):
        """Execute trade on Hibachi"""
        action = decision.get('action', 'HOLD')
        if action not in ['BUY', 'SELL']:
            return

        symbol = decision.get('symbol', 'SOL')
        size = decision.get('size', 0.01)

        logger.info(f"[HIBACHI] Executing {action} {symbol} x{size}")

        if not self.dry_run:
            try:
                side = 'LONG' if action == 'BUY' else 'SHORT'
                result = await self.hibachi_executor.open_position(symbol, side, size)
                if result:
                    self.hibachi_exit_rules.register_position(
                        symbol=symbol,
                        side=side,
                        entry_price=current_price,
                        size=size
                    )
                    logger.info(f"[HIBACHI] Position opened: {side} {symbol} @ {current_price}")
            except Exception as e:
                logger.error(f"[HIBACHI] Trade execution failed: {e}")
        else:
            logger.info(f"[HIBACHI] DRY RUN - Would {action} {symbol}")

    async def _execute_extended_trade(self, decision: Dict, current_price: float):
        """Execute trade on Extended"""
        action = decision.get('action', 'HOLD')
        if action not in ['BUY', 'SELL']:
            return

        symbol = decision.get('symbol', 'ETH')
        size = decision.get('size', 0.01)

        logger.info(f"[EXTENDED] Executing {action} {symbol} x{size}")

        if not self.dry_run:
            try:
                side = 'LONG' if action == 'BUY' else 'SHORT'
                result = await self.extended_executor.open_position(symbol, side, size)
                if result:
                    self.extended_exit_rules.register_position(
                        symbol=symbol,
                        side=side,
                        entry_price=current_price,
                        size=size
                    )
                    logger.info(f"[EXTENDED] Position opened: {side} {symbol} @ {current_price}")
            except Exception as e:
                logger.error(f"[EXTENDED] Trade execution failed: {e}")
        else:
            logger.info(f"[EXTENDED] DRY RUN - Would {action} {symbol}")

    def _print_performance_summary(self):
        """Print performance comparison between strategies"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("A/B TEST PERFORMANCE SUMMARY")
        logger.info("=" * 70)

        for dex, perf in self.performance.items():
            trades = perf['trades']
            wins = perf['wins']
            win_rate = (wins / trades * 100) if trades > 0 else 0
            strategy = self.strategy_a.name if dex == 'hibachi' else self.strategy_b.name

            logger.info(f"[{dex.upper()}] Strategy: {strategy}")
            logger.info(f"  Trades: {trades}")
            logger.info(f"  Wins: {wins} ({win_rate:.1f}%)")
            logger.info(f"  Start Balance: ${perf['start_balance']:.2f}")

        # Print daily stats
        logger.info("")
        logger.info("Daily Trade Limits:")
        hibachi_stats = self.hibachi_exit_rules.get_daily_stats()
        extended_stats = self.extended_exit_rules.get_daily_stats()
        logger.info(f"  [HIBACHI] {hibachi_stats['trades_today']}/{hibachi_stats['max_trades']} trades")
        logger.info(f"  [EXTENDED] {extended_stats['trades_today']}/{extended_stats['max_trades']} trades")
        logger.info("=" * 70)

    async def run_cycle(self):
        """Run one trading cycle on both DEXs"""
        logger.info("")
        logger.info("-" * 50)
        logger.info(f"CYCLE START: {datetime.now().strftime('%H:%M:%S')}")
        logger.info("-" * 50)

        # ========================================
        # HIBACHI (Strategy A: TIME_CAPPED)
        # ========================================
        try:
            # Check existing positions
            hibachi_positions = await self._check_hibachi_positions()

            # Get market data for primary symbol
            hibachi_data = await self._get_hibachi_market_data('SOL')

            if hibachi_data:
                # Make decision
                decision = await self._make_hibachi_decision(hibachi_data, hibachi_positions)

                if decision and decision.get('action') in ['BUY', 'SELL']:
                    await self._execute_hibachi_trade(
                        decision,
                        hibachi_data.get('price', 0)
                    )
        except Exception as e:
            logger.error(f"[HIBACHI] Cycle error: {e}")

        # ========================================
        # EXTENDED (Strategy B: RUNNERS_RUN)
        # ========================================
        try:
            # Check existing positions
            extended_positions = await self._check_extended_positions()

            # Get market data for primary symbol
            extended_data = await self._get_extended_market_data('ETH')

            if extended_data:
                # Make decision
                decision = await self._make_extended_decision(extended_data, extended_positions)

                if decision and decision.get('action') in ['BUY', 'SELL']:
                    await self._execute_extended_trade(
                        decision,
                        extended_data.get('price', 0)
                    )
        except Exception as e:
            logger.error(f"[EXTENDED] Cycle error: {e}")

        logger.info(f"CYCLE END: {datetime.now().strftime('%H:%M:%S')}")

    async def run(self):
        """Main run loop"""
        await self.initialize()

        self.running = True
        cycle_count = 0

        # Use shorter interval for higher volume
        check_interval = min(
            self.strategy_a.check_interval_seconds,
            self.strategy_b.check_interval_seconds
        )

        logger.info(f"Starting A/B Test Bot (check interval: {check_interval}s)")

        while self.running:
            try:
                await self.run_cycle()
                cycle_count += 1

                # Print summary every 6 cycles (1 hour at 10-min intervals)
                if cycle_count % 6 == 0:
                    self._print_performance_summary()

                # Wait for next cycle
                logger.info(f"Next cycle in {check_interval} seconds...")
                await asyncio.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Shutdown requested...")
                self.running = False
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(60)

        self._print_performance_summary()
        logger.info("A/B Test Bot stopped.")


async def main():
    parser = argparse.ArgumentParser(description="A/B Test Trading Bot")
    parser.add_argument('--dry-run', action='store_true', help="Run without executing trades")
    parser.add_argument('--live', action='store_true', help="Execute real trades")
    parser.add_argument('--model', type=str, default='deepseek-chat', help="LLM model to use")

    args = parser.parse_args()

    if not args.live and not args.dry_run:
        print("ERROR: Must specify --dry-run or --live")
        sys.exit(1)

    dry_run = not args.live

    bot = ABTestBot(dry_run=dry_run, model=args.model)
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
