#!/usr/bin/env python3
"""
LLM Trading Bot - Main Entry Point
Integrates all phases: Data Pipeline + LLM Decision + Trade Execution

Usage:
    # Dry-run mode (test without real trades)
    python -m llm_agent.bot_llm --dry-run

    # Live mode (real trades)
    python -m llm_agent.bot_llm --live

    # Single decision mode (for testing)
    python -m llm_agent.bot_llm --dry-run --once
"""

import os
import sys
import time
import asyncio
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_agent.data import MarketDataAggregator
from llm_agent.llm import LLMTradingAgent
from llm_agent.execution import TradeExecutor
from trade_tracker import TradeTracker
from dexes.pacifica.pacifica_sdk import PacificaSDK
from config import GlobalConfig

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/llm_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class LLMTradingBot:
    """Main LLM trading bot orchestrator"""

    def __init__(
        self,
        cambrian_api_key: str,
        deepseek_api_key: str,
        pacifica_api_key: str,
        pacifica_account: str,
        dry_run: bool = True,
        check_interval: int = 300,  # 5 minutes
        position_size: float = 30.0,
        max_positions: int = 3
    ):
        """
        Initialize LLM trading bot

        Args:
            cambrian_api_key: Cambrian API key for macro context
            deepseek_api_key: DeepSeek API key for LLM decisions
            pacifica_api_key: Pacifica API key for trading
            pacifica_account: Pacifica account address
            dry_run: If True, simulate trades without execution (default: True)
            check_interval: Seconds between decision checks (default: 300 = 5 min)
            position_size: USD per trade (default: $30)
            max_positions: Max open positions (default: 3)
        """
        self.dry_run = dry_run
        self.check_interval = check_interval
        self.pacifica_account = pacifica_account

        logger.info(f"Initializing LLM Trading Bot ({['LIVE', 'DRY-RUN'][dry_run]} mode)")

        # Initialize data aggregator
        self.aggregator = MarketDataAggregator(
            cambrian_api_key=cambrian_api_key,
            interval="15m",
            candle_limit=100,
            macro_refresh_hours=12
        )

        # Initialize LLM agent
        self.llm_agent = LLMTradingAgent(
            deepseek_api_key=deepseek_api_key,
            cambrian_api_key=cambrian_api_key,
            model="deepseek-chat",
            max_retries=2,
            daily_spend_limit=10.0,
            max_positions=max_positions
        )

        # Initialize Pacifica SDK (synchronous, simple)
        self.pacifica_sdk = PacificaSDK(
            private_key=pacifica_api_key,
            account_address=pacifica_account
        )

        self.trade_tracker = TradeTracker(dex="pacifica")

        # Initialize trade executor (skip risk_manager for simplicity)
        self.executor = TradeExecutor(
            pacifica_sdk=self.pacifica_sdk,
            trade_tracker=self.trade_tracker,
            dry_run=dry_run,
            default_position_size=position_size,
            max_positions=max_positions
        )

        logger.info("✅ LLM Trading Bot initialized successfully")
        
        # Log prompt version
        prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
        logger.info(f"📝 Active Prompt Version: {prompt_version}")

    def _fetch_open_positions(self):
        """
        Fetch current open positions from Pacifica API and enrich with current price/PnL

        Returns:
            List of position dicts with keys: symbol, side, quantity, entry_price, current_price, pnl, size, time_held
        """
        try:
            import requests
            from datetime import datetime

            response = requests.get(
                f"https://api.pacifica.fi/api/v1/positions",
                params={"account": self.pacifica_account},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success") and result.get("data"):
                    positions = []
                    for pos in result["data"]:
                        symbol = pos["symbol"]
                        side = "LONG" if pos["side"] == "bid" else "SHORT"
                        quantity = float(pos["amount"])
                        entry_price = float(pos["entry_price"])

                        # Get current price from orderbook
                        try:
                            book_response = requests.get(
                                f"https://api.pacifica.fi/api/v1/book",
                                params={"symbol": symbol},
                                timeout=5
                            )
                            book_result = book_response.json()
                            if book_result.get("success") and book_result.get("data"):
                                book = book_result["data"]["l"]
                                if book and len(book) > 0 and len(book[0]) > 0:
                                    best_bid = float(book[0][0]["p"])
                                    best_ask = float(book[1][0]["p"]) if len(book) > 1 and len(book[1]) > 0 else best_bid
                                    current_price = (best_bid + best_ask) / 2
                                else:
                                    current_price = entry_price  # Fallback
                            else:
                                current_price = entry_price  # Fallback
                        except Exception as e:
                            logger.warning(f"Failed to get current price for {symbol}: {e}")
                            current_price = entry_price  # Fallback

                        # Calculate PnL %
                        if entry_price > 0:
                            if side == "LONG":
                                pnl = ((current_price - entry_price) / entry_price) * 100
                            else:  # SHORT
                                pnl = ((entry_price - current_price) / entry_price) * 100
                        else:
                            pnl = 0

                        # Calculate position size in USD
                        size = quantity * current_price

                        # Calculate time held (would need timestamp from API, use placeholder)
                        time_held = "N/A"  # TODO: get from API if available

                        positions.append({
                            "symbol": symbol,
                            "side": side,
                            "quantity": quantity,
                            "entry_price": entry_price,
                            "current_price": current_price,
                            "pnl": pnl,
                            "size": size,
                            "time_held": time_held
                        })

                    logger.info(f"✅ Fetched {len(positions)} open positions from Pacifica")
                    return positions

            logger.warning("Failed to fetch positions from Pacifica API")
            return []

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def run_once(self):
        """Execute one decision cycle"""

        logger.info("=" * 80)
        logger.info(f"Decision Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # Get current open positions from Pacifica API
            open_positions = self._fetch_open_positions()

            logger.info(f"Open positions: {len(open_positions)}")

            # Log market data summary BEFORE decision
            logger.info("=" * 80)
            logger.info("MARKET DATA SUMMARY:")
            logger.info("=" * 80)
            # Get market data and format it
            market_data = self.aggregator.fetch_all_markets()
            if market_data:
                market_summary = self.aggregator.format_market_table(market_data)
                for line in market_summary.split('\n'):
                    logger.info(f"  {line}")
            else:
                logger.info("  No market data available")
            logger.info("=" * 80)

            # Get LLM decision
            logger.info("Getting trading decision from LLM...")
            decision = self.llm_agent.get_trading_decision(
                aggregator=self.aggregator,
                open_positions=open_positions,
                force_macro_refresh=False
            )

            if not decision:
                logger.error("Failed to get decision from LLM")
                return

            # Log decision
            prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
            logger.info("=" * 80)
            logger.info("LLM DECISION:")
            logger.info(f"  Prompt Version: {prompt_version}")
            logger.info(f"  Action: {decision['action']}")
            if decision['symbol']:
                logger.info(f"  Symbol: {decision['symbol']}")
            logger.info(f"  Reason: {decision['reason']}")
            logger.info(f"  Cost: ${decision['cost']:.4f}")
            logger.info("=" * 80)

            # Execute decision
            if decision['action'] != "NOTHING":
                logger.info("Executing decision...")
                result = self.executor.execute_decision(decision)

                if result['success']:
                    logger.info(f"✅ Execution successful: {result['action']} {result['symbol']}")
                    if result['filled_price']:
                        logger.info(f"   Filled: {result['filled_size']:.4f} @ ${result['filled_price']:.2f}")
                else:
                    logger.error(f"❌ Execution failed: {result.get('error')}")
            else:
                logger.info("No action to execute (NOTHING)")

            # Budget status
            logger.info(f"Daily LLM spend: ${self.llm_agent.get_daily_spend():.4f} / $10.00")

        except Exception as e:
            logger.error(f"Error in decision cycle: {e}", exc_info=True)

    def run(self):
        """Run bot continuously"""

        logger.info("Starting LLM Trading Bot main loop")
        logger.info(f"Check interval: {self.check_interval} seconds ({self.check_interval // 60} minutes)")
        prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
        logger.info(f"📝 Active Prompt Version: {prompt_version}")

        try:
            while True:
                self.run_once()

                logger.info(f"Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user (Ctrl+C)")

        except Exception as e:
            logger.error(f"Bot crashed: {e}", exc_info=True)


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description="LLM Trading Bot for Pacifica DEX")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (no real trades)")
    parser.add_argument("--live", action="store_true", help="Run in LIVE mode (real trades)")
    parser.add_argument("--once", action="store_true", help="Run once and exit (for testing)")
    parser.add_argument("--interval", type=int, default=300, help="Check interval in seconds (default: 300 = 5 min)")
    parser.add_argument("--position-size", type=float, default=30.0, help="Position size in USD (default: 30)")
    parser.add_argument("--max-positions", type=int, default=3, help="Max open positions (default: 3)")

    args = parser.parse_args()

    # Validate mode
    if not args.dry_run and not args.live:
        print("ERROR: Must specify either --dry-run or --live")
        sys.exit(1)

    if args.dry_run and args.live:
        print("ERROR: Cannot specify both --dry-run and --live")
        sys.exit(1)

    # Get API keys
    cambrian_api_key = os.getenv("CAMBRIAN_API_KEY")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    pacifica_api_key = os.getenv("PACIFICA_API_KEY")
    pacifica_account = os.getenv("PACIFICA_ACCOUNT")

    if not all([cambrian_api_key, deepseek_api_key, pacifica_api_key, pacifica_account]):
        print("ERROR: Missing required environment variables:")
        if not cambrian_api_key:
            print("  - CAMBRIAN_API_KEY")
        if not deepseek_api_key:
            print("  - DEEPSEEK_API_KEY")
        if not pacifica_api_key:
            print("  - PACIFICA_API_KEY")
        if not pacifica_account:
            print("  - PACIFICA_ACCOUNT")
        sys.exit(1)

    # Initialize bot
    bot = LLMTradingBot(
        cambrian_api_key=cambrian_api_key,
        deepseek_api_key=deepseek_api_key,
        pacifica_api_key=pacifica_api_key,
        pacifica_account=pacifica_account,
        dry_run=args.dry_run,
        check_interval=args.interval,
        position_size=args.position_size,
        max_positions=args.max_positions
    )

    # Run bot
    if args.once:
        logger.info("Running single decision cycle...")
        bot.run_once()
    else:
        bot.run()


if __name__ == "__main__":
    main()
