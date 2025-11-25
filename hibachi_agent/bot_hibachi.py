#!/usr/bin/env python3
"""
Hibachi Trading Bot - Main Entry Point
Mirrors Lighter bot structure, adapted for Hibachi DEX

Usage:
    python -m hibachi_agent.bot_hibachi --dry-run
    python -m hibachi_agent.bot_hibachi --live
    python -m hibachi_agent.bot_hibachi --dry-run --once
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

# Reuse Pacifica bot's LLM system (same structure)
from llm_agent.llm import LLMTradingAgent
from trade_tracker import TradeTracker
from dexes.hibachi import HibachiSDK
from hibachi_agent.execution.hibachi_executor import HibachiTradeExecutor
from hibachi_agent.execution.hard_exit_rules import HardExitRules
from hibachi_agent.data.hibachi_aggregator import HibachiMarketDataAggregator

# Load environment variables from project root
project_root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=project_root_env, override=True)

# Configure clean, human-readable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.FileHandler('logs/hibachi_bot.log'),
        logging.StreamHandler()
    ]
)

# Suppress noisy loggers
logging.getLogger('hibachi_agent.data.hibachi_fetcher').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)
logging.getLogger('dexes.hibachi.hibachi_sdk').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(f"✅ Loaded environment variables from: {project_root_env}")


class HibachiTradingBot:
    """Hibachi trading bot - mirrors Lighter bot structure"""

    def __init__(
        self,
        cambrian_api_key: str,
        deepseek_api_key: str,
        hibachi_api_key: str,
        hibachi_api_secret: str,
        hibachi_account_id: str,
        dry_run: bool = True,
        check_interval: int = 300,  # 5 minutes
        position_size: float = 5.0,  # $5 per trade (~8% of $58 account)
        max_positions: int = 10,
        max_position_age_minutes: int = 240,  # 4 hours
        model: str = "deepseek-chat"  # LLM model to use
    ):
        """
        Initialize Hibachi trading bot

        Args:
            cambrian_api_key: Cambrian API key for macro context
            deepseek_api_key: LLM API key (DeepSeek or OpenRouter depending on model)
            hibachi_api_key: Hibachi API key
            hibachi_api_secret: Hibachi API secret
            hibachi_account_id: Hibachi account ID
            dry_run: If True, simulate trades without execution
            check_interval: Seconds between decision checks (default: 300 = 5 min)
            position_size: USD per trade (default: $5)
            max_positions: Max open positions (default: 10)
            max_position_age_minutes: Max position age in minutes before auto-close (default: 240)
            model: LLM model to use (default: deepseek-chat, options: qwen-max)
        """
        self.dry_run = dry_run
        self.check_interval = check_interval

        logger.info(f"Initializing Hibachi Trading Bot ({['LIVE', 'DRY-RUN'][dry_run]} mode)")

        # Initialize Hibachi SDK
        self.hibachi_sdk = HibachiSDK(
            api_key=hibachi_api_key,
            api_secret=hibachi_api_secret,
            account_id=hibachi_account_id
        )

        # Initialize Hibachi data aggregator
        self.aggregator = HibachiMarketDataAggregator(
            cambrian_api_key=cambrian_api_key,
            sdk=self.hibachi_sdk,
            interval="15m",
            candle_limit=100,
            macro_refresh_hours=12
        )
        logger.info("✅ Using Hibachi DEX data")

        # Initialize symbols
        asyncio.run(self.aggregator.hibachi._initialize_symbols())

        # Initialize LLM agent (same as Lighter/Pacifica)
        self.llm_agent = LLMTradingAgent(
            deepseek_api_key=deepseek_api_key,
            cambrian_api_key=cambrian_api_key,
            model=model,  # Use selected model (deepseek-chat or qwen-max)
            max_retries=2,
            daily_spend_limit=10.0,
            max_positions=max_positions
        )
        logger.info(f"🤖 LLM Model: {model}")

        self.trade_tracker = TradeTracker(dex="hibachi")

        # Initialize executor
        self.executor = HibachiTradeExecutor(
            hibachi_sdk=self.hibachi_sdk,
            trade_tracker=self.trade_tracker,
            dry_run=dry_run,
            default_position_size=position_size,
            max_positions=max_positions,
            max_position_age_minutes=max_position_age_minutes
        )

        # Track last deep research cycle
        self.last_deep_research_time = datetime.now()
        self.deep_research_interval = 3600  # 1 hour

        # Track decisions for hourly review
        self.decision_history = []

        # Store position size for logging
        self.position_size = position_size

        # Initialize hard exit rules - AGGRESSIVE SCALPING (tightened stop-loss)
        self.hard_exit_rules = HardExitRules(
            min_hold_hours=0.25,     # 15 min minimum hold (fast scalps)
            profit_target_pct=1.5,   # Force close at +1.5% (quick profits)
            stop_loss_pct=0.5        # Force close at -0.5% (TIGHTER stop - was 0.8%)
        )
        logger.info("✅ Hard exit rules enabled: 15min min hold, +1.5% target, -0.5% stop (TIGHTER)")

        logger.info("✅ Hibachi Trading Bot initialized successfully")

        # Log prompt version
        prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
        logger.info(f"📝 Active Prompt Version: {prompt_version}")

    async def run_once(self):
        """Run single decision cycle - mirrors Lighter bot structure"""
        current_time = datetime.now()

        logger.info("=" * 80)
        logger.info(f"🔄 Starting decision cycle at {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # Fetch all market data
            logger.info("📊 Fetching market data from Hibachi...")
            market_data_dict = await self.aggregator.fetch_all_markets()

            if not market_data_dict:
                logger.warning("⚠️  No market data available - skipping cycle")
                return

            logger.info(f"✅ Fetched data for {len(market_data_dict)} markets")

            # Get macro context
            macro_context = self.aggregator.get_macro_context()

            # Get current positions from executor
            logger.info("📊 Fetching current positions...")
            raw_positions = await self.executor._fetch_open_positions()

            # Build open_positions list with enriched data
            open_positions = []
            for pos in raw_positions:
                symbol = pos.get('symbol')
                quantity = float(pos.get('quantity', 0))

                if quantity == 0:
                    continue

                direction = pos.get('direction', 'Long')
                side = 'LONG' if direction == 'Long' else 'SHORT'

                # Get tracker data for entry price
                tracker_data = self.trade_tracker.get_open_trade_for_symbol(symbol)
                entry_price = tracker_data.get('entry_price', 0) if tracker_data else 0

                # Get current price
                current_price = await self.hibachi_sdk.get_price(symbol)
                if not current_price:
                    current_price = entry_price

                # Calculate PnL
                if entry_price and entry_price > 0:
                    if side == 'LONG':
                        pnl = (current_price - entry_price) * quantity
                    else:  # SHORT
                        pnl = (entry_price - current_price) * quantity
                else:
                    pnl = 0

                open_positions.append({
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'size': quantity,
                    'pnl': pnl,
                    'direction': direction
                })

            logger.info(f"   Found {len(open_positions)} open positions")

            # Check for stale positions first
            logger.info("🕐 Checking for stale positions...")
            stale_closed = await self.executor.check_stale_positions()
            if stale_closed:
                for symbol in stale_closed:
                    logger.info(f"   ⏰ Aged out {symbol}")
                # Refresh positions after closing stale ones
                raw_positions = await self.executor._fetch_open_positions()
                open_positions = []
                for pos in raw_positions:
                    symbol = pos.get('symbol')
                    quantity = float(pos.get('quantity', 0))
                    if quantity == 0:
                        continue
                    direction = pos.get('direction', 'Long')
                    side = 'LONG' if direction == 'Long' else 'SHORT'
                    tracker_data = self.trade_tracker.get_open_trade_for_symbol(symbol)
                    entry_price = tracker_data.get('entry_price', 0) if tracker_data else 0
                    current_price = await self.hibachi_sdk.get_price(symbol)
                    if not current_price:
                        current_price = entry_price
                    if entry_price and entry_price > 0:
                        if side == 'LONG':
                            pnl = (current_price - entry_price) * quantity
                        else:
                            pnl = (entry_price - current_price) * quantity
                    else:
                        pnl = 0
                    open_positions.append({
                        'symbol': symbol,
                        'side': side,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'size': quantity,
                        'pnl': pnl,
                        'direction': direction
                    })

            # Check hard exit rules BEFORE LLM decision (force closes override LLM)
            logger.info("🛡️  Checking hard exit rules...")
            forced_closes = []
            for position in open_positions[:]:  # Use slice copy to allow modification during iteration
                symbol = position.get('symbol', 'UNKNOWN')
                side = position.get('side', 'UNKNOWN')
                pnl = position.get('pnl', 0)
                entry_price = position.get('entry_price', 0)
                current_price = position.get('current_price', entry_price)

                # Calculate P&L percentage
                if entry_price and entry_price > 0:
                    if side == 'LONG':
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    else:  # SHORT
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                else:
                    pnl_pct = 0

                # Get tracker data for this position (for entry timestamp)
                tracker_data = self.trade_tracker.get_open_trade_for_symbol(symbol)

                # Get market data for this symbol (for RSI/MACD)
                market_data = {}
                if symbol in market_data_dict:
                    market_data = market_data_dict[symbol]

                # Build position dict for hard rules
                position_for_rules = {
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'pnl_pct': pnl_pct / 100  # Convert to decimal
                }

                # Check if should force close
                should_close, reason = self.hard_exit_rules.check_should_force_close(
                    position_for_rules,
                    market_data,
                    tracker_data
                )

                if should_close:
                    forced_closes.append((symbol, reason, pnl_pct))
                    logger.info(f"   ⚡ HARD RULE TRIGGERED: Force closing {symbol} {side} - {reason}")

                    # Execute forced close immediately
                    close_decision = {
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'reasoning': f"HARD RULE: {reason}",
                        'confidence': 1.0
                    }
                    close_result = await self.executor.execute_decision(close_decision)

                    if close_result.get('success'):
                        logger.info(f"      ✅ Forced close executed successfully")
                        # Remove from open_positions list
                        open_positions = [p for p in open_positions if p.get('symbol') != symbol]
                    else:
                        logger.error(f"      ❌ Forced close failed: {close_result.get('error')}")

            if forced_closes:
                logger.info(f"   📊 Executed {len(forced_closes)} forced closes via hard rules")

            # Get macro context only for V1 (V2 doesn't use it)
            prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
            if prompt_version == "v1_original":
                # macro_context already fetched above
                pass
            else:
                macro_context = None  # V2 doesn't use macro context

            # Format market table
            market_table = self.aggregator.format_market_table(market_data_dict)

            # Get account balance
            account_balance = await self.executor._fetch_account_balance()
            if not account_balance:
                account_balance = 0.0
            logger.info(f"💰 Account balance: ${account_balance:.2f}")

            # Get trade history
            trade_history = ""
            if self.trade_tracker:
                recent_trades = self.trade_tracker.get_recent_trades(hours=24, limit=10)
                if recent_trades:
                    trade_history = "\n\nRECENT TRADING HISTORY (Last 24h):\n"
                    trade_history += "Symbol | Side | Entry Price | Exit Price | P&L | Status\n"
                    trade_history += "-" * 70 + "\n"
                    for trade in recent_trades[-10:]:
                        symbol = trade.get('symbol') or 'N/A'
                        side = (trade.get('side') or 'N/A').upper()
                        entry = trade.get('entry_price') or 0
                        exit_price = trade.get('exit_price')
                        pnl = trade.get('pnl') or 0
                        status = trade.get('status') or 'N/A'
                        exit_str = f"${exit_price:.4f}" if exit_price and exit_price != 'N/A' else 'N/A'
                        trade_history += f"{symbol} | {side} | ${entry:.4f} | {exit_str} | ${pnl:.2f} | {status}\n"

            # Get recently closed symbols
            recently_closed = self.trade_tracker.get_recently_closed_symbols(hours=2)

            # Hibachi markets list
            hibachi_symbols = list(market_data_dict.keys())

            # Build kwargs based on prompt version
            prompt_kwargs = {
                "market_table": market_table,
                "open_positions": open_positions,
                "account_balance": account_balance,
                "hourly_review": None,  # Not implemented yet
                "trade_history": trade_history,
                "recently_closed_symbols": recently_closed or [],
                "dex_name": "Hibachi",
                "analyzed_tokens": hibachi_symbols
            }

            # V1 uses macro_context and deep42_context, V2 doesn't
            if prompt_version == "v1_original":
                prompt_kwargs["macro_context"] = macro_context
                # Enable Deep42 multi-timeframe context
                try:
                    enhanced_deep42 = self.aggregator.macro_fetcher.get_enhanced_context()
                    prompt_kwargs["deep42_context"] = enhanced_deep42
                    logger.info("✅ Using Deep42 multi-timeframe context")
                except Exception as e:
                    logger.error(f"Failed to get enhanced Deep42 context: {e}")
                    prompt_kwargs["deep42_context"] = None

            prompt = self.llm_agent.prompt_formatter.format_trading_prompt(**prompt_kwargs)

            # Get trading decision from LLM (same pattern as Lighter bot)
            logger.info("🤖 Getting trading decision from LLM...")

            # Convert market_data_dict to list for validation
            all_symbols = list(market_data_dict.keys())

            # Call LLM with retries
            responses = []
            for attempt in range(self.llm_agent.max_retries + 1):
                logger.info(f"   LLM query attempt {attempt + 1}/{self.llm_agent.max_retries + 1}...")

                # Query model
                result = self.llm_agent.model_client.query(
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.1
                )

                if result is None:
                    logger.error(f"   LLM query failed (attempt {attempt + 1})")
                    continue

                # Add response to list
                responses.append(result["content"])

                # Log full LLM response
                logger.info("")
                logger.info("=" * 80)
                logger.info("🤖 LLM RESPONSE:")
                logger.info("=" * 80)
                for line in result["content"].split('\n'):
                    logger.info(line)
                logger.info("=" * 80)
                logger.info("")

                # Try parsing multiple decisions
                parsed_decisions = self.llm_agent.response_parser.parse_multiple_decisions(result["content"])
                if parsed_decisions is None or len(parsed_decisions) == 0:
                    logger.warning(f"   Parse failed (attempt {attempt + 1}), will retry with clearer prompt")

                    # Modify prompt for retry
                    if attempt < self.llm_agent.max_retries:
                        prompt += (
                            f"\n\nIMPORTANT: Analyze ALL {len(all_symbols)} markets and respond with decisions ONLY for markets with clear signals:\n"
                            "TOKEN: SOL\n"
                            "DECISION: BUY SOL\n"
                            "CONFIDENCE: 0.75\n"
                            "REASON: Your reasoning here\n\n"
                            "Do NOT add any other text before or after."
                        )
                    continue

                # Validate all decisions
                logger.info("")
                logger.info("=" * 80)
                logger.info(f"🔍 VALIDATING {len(parsed_decisions)} DECISIONS FROM LLM")
                logger.info("=" * 80)

                valid_decisions = []
                current_positions = open_positions.copy() if open_positions else []

                for idx, parsed in enumerate(parsed_decisions, 1):
                    symbol = parsed.get("symbol")
                    action = parsed.get("action", "").upper()
                    confidence = parsed.get("confidence", 0.5)
                    reason = parsed.get("reason", "No reason provided")

                    # Normalize symbol format for Hibachi (add /USDT-P if not present)
                    if symbol and not symbol.endswith("/USDT-P"):
                        symbol = f"{symbol}/USDT-P"
                        parsed["symbol"] = symbol  # Update parsed dict

                    logger.info(f"\n[Decision {idx}/{len(parsed_decisions)}]")
                    logger.info(f"  Symbol: {symbol}")
                    logger.info(f"  Action: {action}")
                    logger.info(f"  Confidence: {confidence:.2f}")
                    logger.info(f"  Reason: {reason[:100]}...")

                    # HARD RULE: Prevent LLM from closing before minimum hold time
                    if action == "CLOSE" and symbol:
                        tracker_data = self.trade_tracker.get_open_trade_for_symbol(symbol)
                        if tracker_data:
                            position = next((p for p in open_positions if p.get('symbol') == symbol), None)
                            if position:
                                pnl = position.get('pnl', 0)
                                entry_price = position.get('entry_price', 0)
                                current_price = position.get('current_price', entry_price)
                                side = position.get('side', 'LONG')

                                if entry_price and entry_price > 0:
                                    if side == 'LONG':
                                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                                    else:
                                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                                else:
                                    pnl_pct = 0

                                should_prevent, prevent_reason = self.hard_exit_rules.should_prevent_close(
                                    tracker_data,
                                    pnl_pct
                                )

                                if should_prevent:
                                    logger.warning(f"  🔒 BLOCKED BY HARD RULE: {prevent_reason}")
                                    continue

                    # Check if symbol was recently closed
                    if symbol and symbol in (recently_closed or []) and action in ["BUY", "SELL"]:
                        logger.warning(f"  ⚠️ {action} {symbol}: Recently closed (within 2h)")
                        if confidence < 0.7:
                            logger.warning(f"  ❌ REJECTED: Low confidence ({confidence:.2f}) on recently closed symbol")
                            continue
                        else:
                            logger.info(f"  ✅ ALLOWED: High confidence ({confidence:.2f}) overrides recent close")

                    # Skip if already have position
                    has_position = any(p.get('symbol') == symbol for p in current_positions)
                    if has_position and action in ["BUY", "SELL"]:
                        logger.info(f"  ❌ REJECTED: Already have position in {symbol}")
                        continue

                    # Validate symbol is a Hibachi market
                    if symbol not in self.aggregator.hibachi_markets:
                        logger.warning(f"  ❌ REJECTED: {symbol} is not a Hibachi market")
                        logger.warning(f"  Available: {', '.join(sorted(self.aggregator.hibachi_markets))}")
                        continue
                    else:
                        logger.info(f"  ✅ Symbol validation passed - {symbol} is available on Hibachi")

                    # Validate decision
                    is_valid, error = self.llm_agent.response_parser.validate_decision(
                        parsed,
                        open_positions=current_positions,
                        max_positions=self.llm_agent.max_positions
                    )

                    if is_valid:
                        logger.info(f"  ✅ ACCEPTED: {action} {symbol} validated successfully")
                        valid_decisions.append({
                            "action": action,
                            "symbol": symbol,
                            "reasoning": parsed.get("reason", ""),
                            "confidence": parsed.get("confidence", 0.5),
                            "cost": result.get("cost", 0)
                        })
                        # Track position if opening new
                        if action in ["BUY", "SELL"]:
                            current_positions.append({"symbol": symbol})
                    else:
                        logger.warning(f"  ❌ REJECTED: {error}")

                # Log validation summary
                logger.info("")
                logger.info("=" * 80)
                logger.info(f"📊 VALIDATION SUMMARY:")
                logger.info(f"  Total decisions from LLM: {len(parsed_decisions)}")
                logger.info(f"  Passed validation: {len(valid_decisions)}")
                logger.info(f"  Failed validation: {len(parsed_decisions) - len(valid_decisions)}")
                logger.info("=" * 80)
                logger.info("")

                if valid_decisions:
                    decisions = valid_decisions
                    break
                else:
                    if parsed_decisions:
                        logger.warning(f"All {len(parsed_decisions)} decisions failed validation")
                    if attempt < self.llm_agent.max_retries:
                        continue
            else:
                # All retries failed
                decisions = None

            if not decisions:
                logger.warning("⚠️  No valid decisions from LLM")
                return

            # Handle multiple decisions
            if not isinstance(decisions, list):
                decisions = [decisions]

            # Log decisions
            total_cost = sum(d.get('cost', 0) for d in decisions)
            logger.info("")
            logger.info(f"💡 LLM DECISIONS: {len(decisions)} decision(s) | Cost: ${total_cost:.4f}")

            # Execute each decision
            for i, decision in enumerate(decisions, 1):
                action = decision.get('action')
                symbol = decision.get('symbol', 'N/A')

                # Map BUY/SELL to LONG/SHORT for executor
                if action == "BUY":
                    decision['action'] = "LONG"
                    action = "LONG"
                elif action == "SELL":
                    decision['action'] = "SHORT"
                    action = "SHORT"

                logger.info(f"\n[{i}/{len(decisions)}] {action} {symbol}")
                logger.info(f"   Reasoning: {decision.get('reasoning', 'N/A')}")

                result = await self.executor.execute_decision(decision)

                if result.get('success'):
                    logger.info(f"   ✅ Execution successful")
                else:
                    logger.warning(f"   ⚠️  Execution failed: {result.get('error', 'Unknown')}")

                # Track decision
                self.decision_history.append({
                    'timestamp': current_time,
                    'decision': decision,
                    'result': result
                })

        except Exception as e:
            logger.error(f"❌ Error in decision cycle: {e}", exc_info=True)

        logger.info("=" * 80)
        logger.info("✅ Decision cycle complete")
        logger.info("=" * 80)

    async def run(self):
        """Run continuous trading loop"""
        logger.info("🚀 Starting Hibachi trading bot...")
        logger.info(f"   Mode: {['LIVE', 'DRY-RUN'][self.dry_run]}")
        logger.info(f"   Check Interval: {self.check_interval}s")
        logger.info(f"   Position Size: ${self.position_size}")

        cycle_count = 0

        try:
            while True:
                cycle_count += 1
                logger.info(f"\n{'='*80}")
                logger.info(f"🔄 Cycle {cycle_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"{'='*80}")

                await self.run_once()

                logger.info(f"⏳ Waiting {self.check_interval}s until next cycle...")
                await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("\n👋 Shutting down gracefully...")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Hibachi Trading Bot")
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no real trades)')
    parser.add_argument('--live', action='store_true', help='Live trading mode')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--interval', type=int, default=300, help='Check interval in seconds (default: 300)')
    parser.add_argument('--model', type=str, default='deepseek-chat',
                        choices=['deepseek-chat', 'qwen-max'],
                        help='LLM model to use (default: deepseek-chat, qwen-max = Alpha Arena winner)')

    args = parser.parse_args()

    # Validate arguments
    if not args.dry_run and not args.live:
        logger.error("❌ Must specify either --dry-run or --live")
        sys.exit(1)

    dry_run = not args.live

    # Load environment variables
    cambrian_api_key = os.getenv('CAMBRIAN_API_KEY')
    deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
    openrouter_api_key = os.getenv('OPEN_ROUTER')
    hibachi_api_key = os.getenv('HIBACHI_PUBLIC_KEY')
    hibachi_api_secret = os.getenv('HIBACHI_PRIVATE_KEY')
    hibachi_account_id = os.getenv('HIBACHI_ACCOUNT_ID')

    # Determine which LLM API key to use based on model choice
    model = args.model
    if model == 'qwen-max':
        llm_api_key = openrouter_api_key
        if not llm_api_key:
            logger.error("❌ OPEN_ROUTER env var required for qwen-max model")
            sys.exit(1)
        logger.info(f"🤖 Using Qwen-Max via OpenRouter (Alpha Arena winner!)")
    else:
        llm_api_key = deepseek_api_key
        if not llm_api_key:
            logger.error("❌ DEEPSEEK_API_KEY env var required for deepseek-chat model")
            sys.exit(1)
        logger.info(f"🤖 Using DeepSeek-Chat")

    # Validate required env vars
    missing = []
    if not cambrian_api_key:
        missing.append('CAMBRIAN_API_KEY')
    if not hibachi_api_key:
        missing.append('HIBACHI_PUBLIC_KEY')
    if not hibachi_api_secret:
        missing.append('HIBACHI_PRIVATE_KEY')
    if not hibachi_account_id:
        missing.append('HIBACHI_ACCOUNT_ID')

    if missing:
        logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    # Create bot
    bot = HibachiTradingBot(
        cambrian_api_key=cambrian_api_key,
        deepseek_api_key=llm_api_key,  # Now uses the right key based on model
        hibachi_api_key=hibachi_api_key,
        hibachi_api_secret=hibachi_api_secret,
        hibachi_account_id=hibachi_account_id,
        dry_run=dry_run,
        check_interval=args.interval,
        model=model  # Pass model choice
    )

    # Run bot
    if args.once:
        logger.info("🔄 Running single cycle...")
        asyncio.run(bot.run_once())
        logger.info("✅ Single cycle complete")
    else:
        asyncio.run(bot.run())


if __name__ == "__main__":
    main()
