#!/usr/bin/env python3
"""
Paradex Trading Bot - Zero-Fee High Volume Strategy
Scans orderbook, uses trend analysis, finds best setups, self-learning

Features:
- Full orderbook analysis
- Trend/technical analysis on all markets
- LLM-powered trade decisions
- Self-learning from past trades (every 30 min)
- Background monitoring between decision cycles

Usage:
    python -m paradex_agent.bot_paradex --dry-run
    python -m paradex_agent.bot_paradex --live
    python -m paradex_agent.bot_paradex --live --interval 300
"""

import os
import sys
import time
import asyncio
import logging
import argparse
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from project root
project_root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=project_root_env, override=True)

from llm_agent.llm import LLMTradingAgent
from llm_agent.self_learning import SelfLearning
from trade_tracker import TradeTracker
from paradex_agent.data.paradex_fetcher import ParadexDataFetcher
from paradex_agent.execution.paradex_executor import ParadexTradeExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.FileHandler('logs/paradex_bot.log'),
        logging.StreamHandler()
    ]
)

# Suppress noisy loggers
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class ParadexTradingBot:
    """
    Paradex Trading Bot with LLM strategy and self-learning

    Zero-fee exchange - focus on:
    1. Tight spreads (ETH, BTC, SOL preferred)
    2. High volume opportunities
    3. Technical setups with orderbook confirmation
    """

    def __init__(
        self,
        llm_api_key: str,
        dry_run: bool = True,
        check_interval: int = 300,
        position_size: float = 10.0,
        max_positions: int = 10,
        max_spread_pct: float = 0.1,
        model: str = "deepseek-chat",
        self_learning_interval: int = 1800  # 30 minutes
    ):
        """
        Initialize Paradex trading bot

        Args:
            llm_api_key: LLM API key
            dry_run: If True, simulate trades
            check_interval: Seconds between decision cycles
            position_size: USD per trade
            max_positions: Maximum open positions
            max_spread_pct: Max spread to accept
            model: LLM model to use
            self_learning_interval: Seconds between self-learning cycles
        """
        self.dry_run = dry_run
        self.check_interval = check_interval
        self.position_size = position_size
        self.self_learning_interval = self_learning_interval

        logger.info(f"Initializing Paradex Trading Bot ({'DRY-RUN' if dry_run else 'LIVE'} mode)")

        # Initialize Paradex client
        from paradex_py import ParadexSubkey

        self.paradex = ParadexSubkey(
            env='prod',
            l2_private_key=os.getenv('PARADEX_PRIVATE_SUBKEY'),
            l2_address=os.getenv('PARADEX_ACCOUNT_ADDRESS'),
        )
        logger.info("Paradex client initialized")

        # Initialize data fetcher
        self.fetcher = ParadexDataFetcher(paradex_client=self.paradex)

        # Initialize trade tracker
        self.trade_tracker = TradeTracker(dex="paradex")

        # Initialize executor (0.5% spread for zero-fee volume farming)
        self.executor = ParadexTradeExecutor(
            paradex_client=self.paradex,
            trade_tracker=self.trade_tracker,
            data_fetcher=self.fetcher,
            dry_run=dry_run,
            default_position_size=position_size,
            max_positions=max_positions,
            max_spread_pct=0.5  # Allow 0.5% spread for high volume
        )

        # Initialize LLM agent
        cambrian_api_key = os.getenv('CAMBRIAN_API_KEY', '')
        self.llm_agent = LLMTradingAgent(
            deepseek_api_key=llm_api_key,
            cambrian_api_key=cambrian_api_key,
            model=model,
            max_retries=2,
            daily_spend_limit=10.0,
            max_positions=max_positions
        )
        logger.info(f"LLM Model: {model}")

        # Initialize self-learning
        self.self_learning = SelfLearning(self.trade_tracker, min_trades_for_insight=5)
        self.last_self_learning_time = datetime.now()
        logger.info("Self-learning module initialized")

        # Priority symbols (tightest spreads)
        self.priority_symbols = ['ETH', 'BTC', 'SOL']

        logger.info("Paradex Trading Bot initialized successfully")

    def format_market_table(self, market_data: Dict[str, Dict]) -> str:
        """Format market data as table for LLM"""
        lines = []
        lines.append("=" * 100)
        lines.append("PARADEX MARKET DATA (Zero Fees)")
        lines.append("=" * 100)
        lines.append(
            f"{'Symbol':<8} {'Price':>12} {'Spread%':>8} "
            f"{'RSI':>6} {'MACD':>10} {'OB Imbal':>10} {'Volume':>12}"
        )
        lines.append("-" * 100)

        # Sort by priority (ETH, BTC, SOL first), then alphabetically
        sorted_symbols = sorted(
            market_data.keys(),
            key=lambda s: (0 if s in self.priority_symbols else 1, s)
        )

        for symbol in sorted_symbols:
            data = market_data[symbol]
            price = data.get('price', 0)
            spread = data.get('spread_pct', 0)
            rsi = data.get('rsi', 50)
            macd = data.get('macd_histogram', 0)
            imbalance = data.get('orderbook_imbalance', 0)
            bid_vol = data.get('bid_volume', 0)
            ask_vol = data.get('ask_volume', 0)
            total_vol = bid_vol + ask_vol

            # Format imbalance with direction indicator
            imbal_str = f"{imbalance:+.2f}"
            if imbalance > 0.2:
                imbal_str += " (bullish)"
            elif imbalance < -0.2:
                imbal_str += " (bearish)"

            lines.append(
                f"{symbol:<8} ${price:>11,.2f} {spread:>7.3f}% "
                f"{rsi:>6.1f} {macd:>+10.4f} {imbal_str:>10} ${total_vol:>11,.0f}"
            )

        lines.append("=" * 100)
        return "\n".join(lines)

    def format_positions(self, positions: List[Dict]) -> str:
        """Format open positions for display"""
        if not positions:
            return "Open Positions: None"

        lines = ["Open Positions:"]
        lines.append(f"{'Symbol':<8} {'Side':<6} {'Entry':>12} {'Size':>10} {'P&L':>12}")
        lines.append("-" * 60)

        for pos in positions:
            symbol = pos.get('symbol', 'N/A')
            side = pos.get('side', 'N/A')
            entry = pos.get('entry_price', 0)
            size = pos.get('size', 0)
            pnl = pos.get('unrealized_pnl', 0)

            pnl_str = f"${pnl:+.2f}"
            lines.append(f"{symbol:<8} {side:<6} ${entry:>11,.2f} {size:>10.6f} {pnl_str:>12}")

        return "\n".join(lines)

    async def run_self_learning(self):
        """Run self-learning analysis"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SELF-LEARNING CYCLE")
        logger.info("=" * 60)

        context = self.self_learning.generate_learning_context(hours=168)  # Last 7 days
        if context:
            for line in context.split('\n'):
                logger.info(line)
        else:
            logger.info("Not enough trades for self-learning insights yet")

        self.last_self_learning_time = datetime.now()
        logger.info("=" * 60)

    async def run_once(self):
        """Run single decision cycle"""
        current_time = datetime.now()

        # Check if it's time for self-learning
        time_since_learning = (current_time - self.last_self_learning_time).total_seconds()
        if time_since_learning >= self.self_learning_interval:
            await self.run_self_learning()

        # Cycle header
        logger.info("")
        logger.info("")
        logger.info("=" * 80)
        logger.info(f"PARADEX DECISION CYCLE | {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        logger.info("")

        try:
            # Fetch account summary
            account = self.fetcher.fetch_account_summary()
            account_balance = account.get('account_value', 0)
            logger.info(f"Account Balance: ${account_balance:.2f}")

            # Fetch open positions
            positions = self.fetcher.fetch_positions()
            logger.info("")
            logger.info(self.format_positions(positions))

            # Fetch all market data
            logger.info("")
            logger.info("Fetching market data...")
            market_data = await self.fetcher.fetch_all_markets()

            if not market_data:
                logger.warning("No market data available - skipping cycle")
                return

            logger.info(f"Loaded {len(market_data)} markets")
            logger.info("")

            # Format market table
            market_table = self.format_market_table(market_data)
            logger.info(market_table)

            # Get trade history
            recent_trades = self.trade_tracker.get_recent_trades(hours=24, limit=10)
            trade_history = ""
            if recent_trades:
                trade_history = "\n\nRECENT TRADES (Last 24h):\n"
                for trade in recent_trades[-5:]:
                    symbol = trade.get('symbol', 'N/A')
                    side = trade.get('side', 'N/A')
                    pnl = trade.get('pnl') or 0  # Handle None pnl
                    status = trade.get('status', 'N/A')
                    trade_history += f"  {symbol} {side}: ${pnl:+.2f} ({status})\n"

            # Get self-learning context
            learning_context = self.self_learning.generate_learning_context(hours=168)

            # Build prompt
            analyzed_symbols = list(market_data.keys())
            prompt = self.llm_agent.prompt_formatter.format_trading_prompt(
                market_table=market_table,
                open_positions=positions,
                account_balance=account_balance,
                trade_history=trade_history,
                analyzed_tokens=analyzed_symbols,
                dex_name="Paradex",
                learning_context=learning_context
            )

            # Get LLM decision
            logger.info("")
            logger.info("Getting trading decision from LLM...")

            result = self.llm_agent.model_client.query(
                prompt=prompt,
                max_tokens=1500,  # More tokens for multiple decisions
                temperature=0.3   # Slightly more creative for finding trades
            )

            if not result:
                logger.error("LLM query failed")
                return

            # Log LLM response
            logger.info("")
            logger.info("=" * 60)
            logger.info("LLM RESPONSE:")
            logger.info("=" * 60)
            for line in result["content"].split('\n'):
                logger.info(line)
            logger.info("=" * 60)

            # Parse decisions
            parsed_decisions = self.llm_agent.response_parser.parse_multiple_decisions(result["content"])

            if not parsed_decisions:
                logger.info("No actionable decisions from LLM")
                return

            # Validate and execute decisions
            logger.info("")
            logger.info(f"Processing {len(parsed_decisions)} decisions...")

            for decision in parsed_decisions:
                symbol = decision.get('symbol')
                action = decision.get('action', '').upper()
                confidence = decision.get('confidence', 0.5)
                reason = decision.get('reason', '')

                # Skip if symbol not in our market data
                if symbol not in market_data and action in ['BUY', 'SELL']:
                    logger.warning(f"Skipping {action} {symbol} - not a Paradex market")
                    continue

                # Check spread for new positions (0.5% for high volume strategy)
                if action in ['BUY', 'SELL']:
                    spread = market_data.get(symbol, {}).get('spread_pct', 999)
                    if spread > 0.5:  # 0.5% max spread for zero-fee volume farming
                        logger.warning(f"Skipping {action} {symbol} - spread too wide ({spread:.3f}%)")
                        continue

                logger.info(f"Executing: {action} {symbol} (confidence: {confidence:.2f})")

                exec_result = await self.executor.execute_decision({
                    'action': action,
                    'symbol': symbol,
                    'confidence': confidence,
                    'reason': reason
                })

                if exec_result.get('success'):
                    logger.info(f"  SUCCESS: {exec_result}")
                else:
                    logger.warning(f"  FAILED: {exec_result.get('error')}")

            # Cycle complete
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"CYCLE COMPLETE | {datetime.now().strftime('%H:%M:%S')}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Cycle error: {e}", exc_info=True)

    async def run_background_monitor(self):
        """
        Background monitor that runs between decision cycles
        Checks for exit conditions more frequently
        """
        monitor_interval = 30  # Check every 30 seconds for fast exits

        while True:
            await asyncio.sleep(monitor_interval)

            try:
                positions = self.fetcher.fetch_positions()
                if not positions:
                    continue

                for pos in positions:
                    symbol = pos.get('symbol')
                    pnl = pos.get('unrealized_pnl', 0)
                    entry = pos.get('entry_price', 0)
                    size = pos.get('size', 0)

                    # Calculate P&L percentage
                    if entry > 0 and size > 0:
                        current_bbo = self.fetcher.fetch_bbo(symbol)
                        if current_bbo:
                            current_price = current_bbo.get('mid_price', 0)
                            if pos['side'] == 'LONG':
                                pnl_pct = ((current_price - entry) / entry) * 100
                            else:
                                pnl_pct = ((entry - current_price) / entry) * 100

                            # HIGH VOLUME quick exit conditions (tight targets for fast rotation)
                            if pnl_pct >= 0.4:  # +0.4% take profit (quick scalp)
                                logger.info(f"🎯 TAKE PROFIT: {symbol} +{pnl_pct:.2f}% - closing for rotation")
                                await self.executor._close_position(symbol, f"Take profit +{pnl_pct:.2f}%")

                            elif pnl_pct <= -0.3:  # -0.3% stop loss (cut fast)
                                logger.info(f"🛑 STOP LOSS: {symbol} {pnl_pct:.2f}% - cutting for rotation")
                                await self.executor._close_position(symbol, f"Stop loss {pnl_pct:.2f}%")

            except Exception as e:
                logger.debug(f"Background monitor error: {e}")

    async def run(self):
        """Main bot loop"""
        logger.info("Starting Paradex Trading Bot")
        logger.info(f"Check interval: {self.check_interval}s ({self.check_interval // 60} min)")
        logger.info(f"Self-learning interval: {self.self_learning_interval}s ({self.self_learning_interval // 60} min)")
        logger.info(f"Position size: ${self.position_size}")

        # Start background monitor
        monitor_task = asyncio.create_task(self.run_background_monitor())

        try:
            while True:
                await self.run_once()

                next_cycle = datetime.now() + timedelta(seconds=self.check_interval)
                logger.info("")
                logger.info(f"Next cycle at: {next_cycle.strftime('%H:%M:%S')} (in {self.check_interval}s)")
                logger.info("")

                await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            monitor_task.cancel()
        except Exception as e:
            logger.error(f"Bot crashed: {e}", exc_info=True)
            monitor_task.cancel()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Paradex Trading Bot")
    parser.add_argument("--live", action="store_true", help="Enable live trading")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry run mode")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=300, help="Check interval in seconds")
    parser.add_argument("--position-size", type=float, default=10.0, help="USD per trade")
    parser.add_argument("--max-positions", type=int, default=10, help="Max open positions")
    parser.add_argument("--model", type=str, default="qwen-max", help="LLM model")

    args = parser.parse_args()

    # Determine mode
    dry_run = not args.live
    if args.live:
        logger.warning("LIVE TRADING MODE ENABLED")
    else:
        logger.info("Dry-run mode (no real trades)")

    # Get API keys - Use OpenRouter for Qwen
    llm_api_key = os.getenv("OPEN_ROUTER")
    if not llm_api_key:
        logger.error("OPEN_ROUTER not set in .env")
        sys.exit(1)

    paradex_key = os.getenv("PARADEX_PRIVATE_SUBKEY")
    if not paradex_key:
        logger.error("PARADEX_PRIVATE_SUBKEY not set")
        sys.exit(1)

    # Initialize bot
    bot = ParadexTradingBot(
        llm_api_key=llm_api_key,
        dry_run=dry_run,
        check_interval=args.interval,
        position_size=args.position_size,
        max_positions=args.max_positions,
        model=args.model
    )

    # Run
    if args.once:
        logger.info("Running single decision cycle...")
        asyncio.run(bot.run_once())
    else:
        asyncio.run(bot.run())


if __name__ == "__main__":
    main()
