#!/usr/bin/env python3
"""
Lighter Trading Bot - Main Entry Point
Mirrors Pacifica bot structure, adapted for Lighter DEX

Usage:
    python -m lighter_agent.bot_lighter --dry-run
    python -m lighter_agent.bot_lighter --live
    python -m lighter_agent.bot_lighter --dry-run --once
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
from dexes.lighter.lighter_sdk import LighterSDK
from lighter_agent.execution.lighter_executor import LighterTradeExecutor
from lighter_agent.execution.hard_exit_rules import HardExitRules
from lighter_agent.data.lighter_aggregator import LighterMarketDataAggregator

# Load environment variables from project root
project_root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=project_root_env, override=True)

# Configure clean, human-readable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s',
    handlers=[
        logging.FileHandler('logs/lighter_bot.log'),
        logging.StreamHandler()
    ]
)

# Suppress noisy loggers
logging.getLogger('lighter_agent.data.lighter_fetcher').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)
logging.getLogger('dexes.lighter.lighter_sdk').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(f"✅ Loaded environment variables from: {project_root_env}")


class LighterTradingBot:
    """Lighter trading bot - mirrors Pacifica bot structure"""

    def __init__(
        self,
        cambrian_api_key: str,
        deepseek_api_key: str,
        lighter_private_key: str,
        lighter_account_index: int,
        lighter_api_key_index: int,
        dry_run: bool = True,
        check_interval: int = 300,  # 5 minutes (same as Pacifica)
        position_size: float = 2.0,  # $2 per trade (reduced for v4 momentum strategy)
        max_positions: int = 15,  # Same as Pacifica bot
        max_position_age_minutes: int = 240,  # 4 hours (v4 strategy: let winners run longer)
        favor_zk_zec: bool = False  # Disabled: ZK/ZEC are proven losers (35.7% and 34.5% WR)
    ):
        """
        Initialize Lighter trading bot

        Args:
            cambrian_api_key: Cambrian API key for macro context
            deepseek_api_key: DeepSeek API key for LLM decisions
            lighter_private_key: Lighter API private key
            lighter_account_index: Lighter account index
            lighter_api_key_index: Lighter API key index
            dry_run: If True, simulate trades without execution
            check_interval: Seconds between decision checks (default: 300 = 5 min)
            position_size: USD per trade (default: $2)
            max_positions: Max open positions (default: 15)
            max_position_age_minutes: Max position age in minutes before auto-close (default: 240)
            favor_zk_zec: Enable ZK/ZEC position weighting (default: False)
        """
        self.dry_run = dry_run
        self.check_interval = check_interval

        logger.info(f"Initializing Lighter Trading Bot ({['LIVE', 'DRY-RUN'][dry_run]} mode)")

        # Initialize Lighter data aggregator (uses Lighter API, not Pacifica!)
        self.aggregator = LighterMarketDataAggregator(
            cambrian_api_key=cambrian_api_key,
            interval="15m",
            candle_limit=100,
            macro_refresh_hours=12
        )
        logger.info("✅ Using Lighter DEX data (not Pacifica)")

        # Initialize LLM agent (same as Pacifica - uses shared rate limiter)
        self.llm_agent = LLMTradingAgent(
            deepseek_api_key=deepseek_api_key,
            cambrian_api_key=cambrian_api_key,
            model="deepseek-chat",
            max_retries=2,
            daily_spend_limit=10.0,  # Shared with Pacifica bot
            max_positions=max_positions
        )

        # Store SDK initialization params (will initialize in async context)
        self.lighter_private_key = lighter_private_key
        self.lighter_account_index = lighter_account_index
        self.lighter_api_key_index = lighter_api_key_index
        self.lighter_sdk = None  # Will be initialized in async context

        self.trade_tracker = TradeTracker(dex="lighter")

        # Store executor params (will initialize after SDK)
        self.executor = None
        self._executor_params = {
            "trade_tracker": self.trade_tracker,
            "dry_run": dry_run,
            "default_position_size": position_size,
            "max_positions": max_positions,
            "max_position_age_minutes": max_position_age_minutes,  # Nov 7 learning
            "favor_zk_zec": favor_zk_zec  # Nov 7 learning
        }

        # Track last deep research cycle (hourly - same as Pacifica)
        self.last_deep_research_time = datetime.now()
        self.deep_research_interval = 3600  # 1 hour

        # Track decisions for hourly review
        self.decision_history = []

        # Store position size for logging
        self.position_size = position_size

        # Initialize hard exit rules (override LLM discretion)
        self.hard_exit_rules = HardExitRules(
            min_hold_hours=2.0,      # 2 hour minimum hold
            profit_target_pct=2.0,   # Force close at +2%
            stop_loss_pct=1.5        # Force close at -1.5%
        )
        logger.info("✅ Hard exit rules enabled: 2h min hold, +2% target, -1.5% stop")

        logger.info("✅ Lighter Trading Bot initialized successfully")
        
        # Log prompt version
        prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
        logger.info(f"📝 Active Prompt Version: {prompt_version}")

    def _generate_hourly_review(self) -> Optional[str]:
        """Generate hourly deep research review (same as Pacifica bot)"""
        # TODO: Implement same as Pacifica bot's _generate_hourly_review
        return None

    def _detect_market_regime(self, market_data_dict: Dict) -> str:
        """
        Detect market regime based on Nov 7 analysis

        Nov 7 was a "volatility flush" day:
        - Many symbols deeply oversold (RSI < 30)
        - Mean reversion opportunities
        - ZK/ZEC showed strongest patterns

        Returns:
            "OVERSOLD_FLUSH" or "NORMAL"
        """
        if not market_data_dict:
            return "NORMAL"

        # Count deeply oversold symbols (RSI < 30)
        oversold_count = 0
        total_with_rsi = 0

        for symbol, data in market_data_dict.items():
            rsi = data.get('rsi')
            if rsi is not None:
                total_with_rsi += 1
                if rsi < 30:
                    oversold_count += 1

        if total_with_rsi == 0:
            return "NORMAL"

        # Calculate oversold percentage
        oversold_pct = (oversold_count / total_with_rsi) * 100

        # Nov 7 threshold: >20 oversold symbols = flush day
        # Adjust threshold based on total markets (20 out of ~100 = 20%)
        oversold_threshold_pct = 15.0  # 15% of markets deeply oversold

        if oversold_pct >= oversold_threshold_pct:
            logger.info(
                f"🌊 MARKET REGIME: OVERSOLD_FLUSH detected! "
                f"{oversold_count}/{total_with_rsi} symbols ({oversold_pct:.1f}%) with RSI < 30 "
                f"(threshold: {oversold_threshold_pct:.0f}%)"
            )
            logger.info(f"   Nov 7 conditions replicated - mean reversion opportunities likely!")
            return "OVERSOLD_FLUSH"
        else:
            logger.debug(
                f"Market regime: NORMAL ({oversold_count}/{total_with_rsi} oversold = {oversold_pct:.1f}%)"
            )
            return "NORMAL"


    async def _ensure_sdk_initialized(self):
        """Initialize SDK in async context (lazy initialization)"""
        if self.lighter_sdk is None:
            logger.info("Initializing Lighter SDK...")
            self.lighter_sdk = LighterSDK(
                private_key=self.lighter_private_key,
                account_index=self.lighter_account_index,
                api_key_index=self.lighter_api_key_index
            )

            # CRITICAL: Set SDK reference in data fetcher for dynamic symbol loading
            self.aggregator.lighter.sdk = self.lighter_sdk

            # Set up Lighter APIs for data fetcher (use SDK's existing api_client)
            import lighter
            # Use the SDK's existing api_client (already initialized in LighterSDK)
            self.aggregator.candlestick_api = lighter.CandlestickApi(self.lighter_sdk.api_client)
            self.aggregator.funding_api = lighter.FundingApi(self.lighter_sdk.api_client)

            # Initialize symbols eagerly now that SDK is available
            await self.aggregator.lighter._initialize_symbols()

            # Initialize executor now that SDK is ready
            if self.executor is None:
                self.executor = LighterTradeExecutor(
                    lighter_sdk=self.lighter_sdk,
                    **self._executor_params
                )
            logger.info("✅ Lighter SDK initialized")

    async def run_once(self):
        """Run single decision cycle - mirrors Pacifica bot structure"""
        # Ensure SDK is initialized (lazy initialization in async context)
        await self._ensure_sdk_initialized()
        
        current_time = datetime.now()
        
        # Check if it's time for hourly deep research cycle
        time_since_last_research = (current_time - self.last_deep_research_time).total_seconds()
        is_deep_research_cycle = time_since_last_research >= self.deep_research_interval

        # Clean, scannable cycle header with clear START marker
        prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
        version_label = "V2" if prompt_version == "v2_deep_reasoning" else "V1"

        logger.info("")
        logger.info("")
        logger.info("╔" + "═" * 78 + "╗")
        if is_deep_research_cycle:
            logger.info(f"║ 🔬 DEEP RESEARCH CYCLE START | {current_time.strftime('%Y-%m-%d %H:%M:%S')} | {version_label:<37} ║")
        else:
            logger.info(f"║ 🤖 DECISION CYCLE START | {current_time.strftime('%Y-%m-%d %H:%M:%S')} | {version_label:<43} ║")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("")

        try:

            # Get ALL positions from Lighter API (for reference)
            positions_result = await self.lighter_sdk.get_positions()
            all_exchange_positions = []
            if positions_result.get('success') and positions_result.get('data'):
                for pos in positions_result['data']:
                    symbol = pos.get('symbol', f"UNKNOWN(market_id={pos.get('market_id')})")
                    all_exchange_positions.append({
                        'symbol': symbol,
                        'side': pos.get('side', 'LONG'),
                        'entry_price': pos.get('entry_price', 0),
                        'current_price': pos.get('entry_price', 0),
                        'size': pos.get('size', 0),
                        'pnl': pos.get('pnl', 0),
                        'market_id': pos.get('market_id')
                    })

            # Use ALL positions on the exchange - we manage everything
            open_positions = all_exchange_positions

            # Check for stale positions and close them (Nov 7 learning: Quick exits work)
            logger.info("")
            closed_stale = await self.executor.check_stale_positions()
            if closed_stale:
                logger.info(f"🔄 Closed {len(closed_stale)} stale positions: {', '.join(closed_stale)}")
                # Refresh positions after closing
                positions_result = await self.lighter_sdk.get_positions()
                all_exchange_positions = []
                if positions_result.get('success') and positions_result.get('data'):
                    for pos in positions_result['data']:
                        symbol = pos.get('symbol', f"UNKNOWN(market_id={pos.get('market_id')})")
                        all_exchange_positions.append({
                            'symbol': symbol,
                            'side': pos.get('side', 'LONG'),
                            'entry_price': pos.get('entry_price', 0),
                            'current_price': pos.get('entry_price', 0),
                            'size': pos.get('size', 0),
                            'pnl': pos.get('pnl', 0),
                            'market_id': pos.get('market_id')
                        })
                open_positions = all_exchange_positions

            # Clean position summary with timestamp
            timestamp_str = datetime.now().strftime('%H:%M:%S')
            logger.info("")
            logger.info(f"┌─ POSITIONS ({timestamp_str}) " + "─" * 57)
            if open_positions:
                for p in open_positions:
                    pnl_emoji = "🟢" if p['pnl'] >= 0 else "🔴"
                    logger.info(f"│ {pnl_emoji} {p['symbol']:<8} {p['side']:<5} ${p['entry_price']:.4f} → P&L: ${p['pnl']:>+7.2f}")
                logger.info(f"└─ {len(open_positions)} position(s) open")
            else:
                logger.info(f"│ No open positions")
                logger.info(f"└─ 0 positions")

            # Fetch market data (condensed logging with timestamp)
            fetch_start = datetime.now()
            logger.info("")
            logger.info(f"┌─ MARKET DATA ({fetch_start.strftime('%H:%M:%S')}) " + "─" * 55)
            logger.info("│ ⏳ Fetching markets from Lighter...")

            all_market_data_dict = await self.aggregator.fetch_all_markets()

            fetch_end = datetime.now()
            fetch_duration = (fetch_end - fetch_start).total_seconds()
            if all_market_data_dict:
                logger.info(f"│ ✅ Loaded {len(all_market_data_dict)} markets in {fetch_duration:.1f}s")
                logger.info("└─" + "─" * 76)
                logger.info("")
                # Show market summary table
                market_summary = self.aggregator.format_market_table(all_market_data_dict)
                for line in market_summary.split('\n'):
                    if line.strip():
                        logger.info(line)
            else:
                logger.info("│ ❌ No market data available")
                logger.info("└─" + "─" * 76)
            
            # Use all market data - show everything to LLM
            market_data_dict = all_market_data_dict.copy() if all_market_data_dict else {}
            
            # Convert back to list for compatibility with rest of code
            market_data_list = list(market_data_dict.values())
            
            # Only analyze Lighter markets
            lighter_symbols = list(market_data_dict.keys())
            logger.info(f"📊 Analyzing {len(lighter_symbols)} Lighter markets: {', '.join(lighter_symbols)}")

            # Check hard exit rules BEFORE LLM decision (force closes override LLM)
            logger.info("")
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
                    logger.info(f"⚡ HARD RULE TRIGGERED: Force closing {symbol} {side} - {reason}")

                    # Execute forced close immediately
                    close_decision = {
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'reason': f"HARD RULE: {reason}",
                        'confidence': 1.0,
                        'current_price': current_price
                    }
                    close_result = await self.executor.execute_decision(close_decision)

                    if close_result.get('success'):
                        logger.info(f"   ✅ Forced close executed successfully")
                        # Remove from open_positions list
                        open_positions = [p for p in open_positions if p.get('symbol') != symbol]
                    else:
                        logger.error(f"   ❌ Forced close failed: {close_result.get('error')}")

            if forced_closes:
                logger.info(f"📊 Executed {len(forced_closes)} forced closes via hard rules")
                # Refresh positions after forced closes
                positions_result = await self.lighter_sdk.get_positions()
                all_exchange_positions = []
                if positions_result.get('success') and positions_result.get('data'):
                    for pos in positions_result['data']:
                        symbol = pos.get('symbol', f"UNKNOWN(market_id={pos.get('market_id')})")
                        all_exchange_positions.append({
                            'symbol': symbol,
                            'side': pos.get('side', 'LONG'),
                            'entry_price': pos.get('entry_price', 0),
                            'current_price': pos.get('entry_price', 0),
                            'size': pos.get('size', 0),
                            'pnl': pos.get('pnl', 0),
                            'market_id': pos.get('market_id')
                        })
                open_positions = all_exchange_positions
            else:
                logger.info("✅ No hard rule triggers - all positions within targets")

            # Detect market regime (Nov 7 learning: Oversold flush days are golden)
            market_regime = self._detect_market_regime(market_data_dict)
            if market_regime == "OVERSOLD_FLUSH":
                logger.info("🚀 STRATEGY BIAS: Favor mean-reversion entries on oversold symbols (ZK/ZEC priority)")

            # Get recently closed symbols (soft warning)
            recently_closed = self.trade_tracker.get_recently_closed_symbols(hours=2)
            if recently_closed:
                logger.info(f"⚠️ Recently closed symbols (last 2h): {recently_closed} - Will allow if high confidence")

            # Generate hourly deep research review if needed
            hourly_review = None
            if is_deep_research_cycle:
                hourly_review = self._generate_hourly_review()
                if hourly_review:
                    logger.info("=" * 80)
                    logger.info("📊 HOURLY REVIEW SUMMARY:")
                    logger.info("=" * 80)
                    for line in hourly_review.split('\n')[:50]:  # Show first 50 lines
                        logger.info(f"  {line}")
                    logger.info("=" * 80)
                # Update last deep research time
                self.last_deep_research_time = current_time

            if not market_data_list:
                logger.warning("No market data available - skipping cycle")
                return

            # Get macro context only for V1 (V2 doesn't use it)
            prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
            if prompt_version == "v1_original":
                macro_context = self.aggregator.get_macro_context()
            else:
                macro_context = None  # V2 doesn't use macro context

            # Format market table (use dict, not list)
            # IMPORTANT: Only show positions we're managing in the prompt
            # Create filtered market data that excludes unmanaged positions' positions info
            market_table = self.aggregator.format_market_table(market_data_dict)

            # Get account balance
            balance = await self.lighter_sdk.get_balance()
            account_balance = balance if balance else 0.0
            if account_balance:
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

            # Format prompt - V2 doesn't accept macro_context/deep42_context
            # (prompt_version already fetched above when checking macro context)

            # Build kwargs based on prompt version
            prompt_kwargs = {
                "market_table": market_table,
                "open_positions": open_positions,
                "account_balance": account_balance,
                "hourly_review": hourly_review,
                "trade_history": trade_history,
                "recently_closed_symbols": recently_closed or [],
                "dex_name": "Lighter",  # Tell prompt formatter to use Lighter-specific instructions
                "analyzed_tokens": lighter_symbols  # Pass symbol list for prompt
            }

            # V1 uses macro_context and deep42_context, V2 doesn't
            if prompt_version == "v1_original":
                prompt_kwargs["macro_context"] = macro_context
                # Enable Deep42 multi-timeframe context (1h regime, 4h BTC health, 6h macro)
                try:
                    enhanced_deep42 = self.aggregator.macro_fetcher.get_enhanced_context()
                    prompt_kwargs["deep42_context"] = enhanced_deep42
                    logger.info("✅ Using Deep42 multi-timeframe context (1h regime, 4h BTC, 6h macro)")
                except Exception as e:
                    logger.error(f"Failed to get enhanced Deep42 context: {e}")
                    prompt_kwargs["deep42_context"] = None

            prompt = self.llm_agent.prompt_formatter.format_trading_prompt(**prompt_kwargs)

            # Get trading decision from LLM (same pattern as Pacifica bot)
            logger.info("Getting trading decision from LLM...")
            
            # Convert market_data_dict to list for validation
            all_symbols = list(market_data_dict.keys())
            
            # Call LLM with retries (same as Pacifica's get_trading_decision)
            responses = []
            for attempt in range(self.llm_agent.max_retries + 1):
                logger.info(f"LLM query attempt {attempt + 1}/{self.llm_agent.max_retries + 1}...")

                # Query model (same parameters as Pacifica)
                result = self.llm_agent.model_client.query(
                    prompt=prompt,
                    max_tokens=500,
                    temperature=0.1
                )

                if result is None:
                    logger.error(f"LLM query failed (attempt {attempt + 1})")
                    continue

                # Add response to list
                responses.append(result["content"])

                # Log full LLM response for transparency
                logger.info("")
                logger.info("=" * 80)
                logger.info("🤖 LLM RESPONSE:")
                logger.info("=" * 80)
                for line in result["content"].split('\n'):
                    logger.info(line)
                logger.info("=" * 80)
                logger.info("")

                # Try parsing multiple decisions (same parser as Pacifica)
                parsed_decisions = self.llm_agent.response_parser.parse_multiple_decisions(result["content"])
                if parsed_decisions is None or len(parsed_decisions) == 0:
                    logger.warning(f"Parse failed (attempt {attempt + 1}), will retry with clearer prompt")

                    # Modify prompt for retry (same as Pacifica)
                    if attempt < self.llm_agent.max_retries:
                        prompt += (
                            f"\n\nIMPORTANT: Analyze ALL {len(all_symbols)} markets below and respond with decisions ONLY for markets with clear trading signals:\n"
                            "TOKEN: BTC\n"
                            "DECISION: BUY BTC\n"
                            "CONFIDENCE: 0.75\n"
                            "REASON: Your reasoning here\n\n"
                            "TOKEN: SOL\n"
                            "DECISION: SELL SOL\n"
                            "CONFIDENCE: 0.65\n"
                            "REASON: Your reasoning here\n\n"
                            "Do NOT add any other text before or after."
                        )
                    continue

                # Validate all decisions (same validation as Pacifica)
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

                    logger.info(f"\n[Decision {idx}/{len(parsed_decisions)}]")
                    logger.info(f"  Symbol: {symbol}")
                    logger.info(f"  Action: {action}")
                    logger.info(f"  Confidence: {confidence:.2f}")
                    logger.info(f"  Reason: {reason[:100]}...")  # First 100 chars

                    # HARD RULE: Prevent LLM from closing before minimum hold time
                    if action == "CLOSE" and symbol:
                        # Get tracker data to check hold time
                        tracker_data = self.trade_tracker.get_open_trade_for_symbol(symbol)
                        if tracker_data:
                            # Get current position to calculate P&L
                            position = next((p for p in open_positions if p.get('symbol') == symbol), None)
                            if position:
                                pnl = position.get('pnl', 0)
                                entry_price = position.get('entry_price', 0)
                                current_price = position.get('current_price', entry_price)
                                side = position.get('side', 'LONG')

                                # Calculate P&L percentage
                                if entry_price and entry_price > 0:
                                    if side == 'LONG':
                                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                                    else:  # SHORT
                                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                                else:
                                    pnl_pct = 0

                                # Check if should prevent close (min hold time not met)
                                should_prevent, prevent_reason = self.hard_exit_rules.should_prevent_close(
                                    tracker_data,
                                    pnl_pct
                                )

                                if should_prevent:
                                    logger.warning(f"  🔒 BLOCKED BY HARD RULE: {prevent_reason}")
                                    logger.warning(f"     LLM wanted to close, but minimum hold time not met")
                                    continue  # Skip this CLOSE decision

                    # Check if symbol was recently closed (prevent immediate re-entry)
                    # Only block if confidence is low (< 0.7) - allow high confidence trades (same as Pacifica)
                    if symbol and symbol in (recently_closed or []) and action in ["BUY", "SELL"]:
                        logger.warning(f"  ⚠️ {action} {symbol}: Recently closed (within 2h) - checking confidence")
                        # Don't block - just warn. Let the LLM's confidence decide.
                        # Only block if confidence is low (< 0.7)
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

                    # Validate symbol is a Lighter market (use aggregator's dynamic list from API)
                    if symbol not in self.aggregator.lighter_markets:
                        logger.warning(f"  ❌ REJECTED: {symbol} is not a Lighter market")
                        logger.warning(f"  Available Lighter markets: {', '.join(sorted(self.aggregator.lighter_markets)[:20])}... (101 total)")
                        continue
                    else:
                        logger.info(f"  ✅ Symbol validation passed - {symbol} is available on Lighter")
                    
                    # Validate decision (same as Pacifica)
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
                            "reason": parsed.get("reason", ""),
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
                logger.error("Failed to get decision from LLM")
                return

            # Handle multiple decisions (same as Pacifica)
            if not isinstance(decisions, list):
                decisions = [decisions]  # Backward compatibility

            # Clean LLM decision output with FULL reasoning (not truncated)
            prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
            total_cost = sum(d.get('cost', 0) for d in decisions)
            llm_timestamp = datetime.now().strftime('%H:%M:%S')

            logger.info("")
            logger.info(f"┌─ LLM DECISIONS ({llm_timestamp}) " + "─" * 52)
            logger.info(f"│ 📋 {len(decisions)} decision(s) | Version: {version_label} | Cost: ${total_cost:.4f}")
            logger.info("├" + "─" * 77)

            # Track decisions for hourly review
            current_time_str = datetime.now().isoformat()

            for i, decision in enumerate(decisions, 1):
                action_emoji = {"BUY": "🟢", "SELL": "🔴", "CLOSE": "🔵", "NOTHING": "⚪"}.get(decision['action'], "❓")
                symbol = decision.get('symbol', 'N/A')
                confidence = decision.get('confidence', 0.5)
                # Show FULL reasoning (not truncated) - break into multiple lines if needed
                full_reason = decision.get('reason', '').strip()

                logger.info(f"│ {action_emoji} [{i}] {decision['action']:<8} {symbol:<8} @{confidence:.2f}")

                # Format reasoning with line breaks and indentation
                if full_reason:
                    # Split long reasoning into multiple lines (70 chars per line)
                    reason_lines = []
                    words = full_reason.split()
                    current_line = ""
                    for word in words:
                        if len(current_line) + len(word) + 1 <= 70:
                            current_line += (" " if current_line else "") + word
                        else:
                            if current_line:
                                reason_lines.append(current_line)
                            current_line = word
                    if current_line:
                        reason_lines.append(current_line)

                    # Log each line with proper indentation
                    for line in reason_lines:
                        logger.info(f"│     {line}")
                
                # Store decision for hourly review
                decision_record = {
                    'timestamp': current_time_str,
                    'action': decision.get('action', 'UNKNOWN'),
                    'symbol': decision.get('symbol'),
                    'side': decision.get('side'),
                    'confidence': decision.get('confidence', 0.5),
                    'reason': decision.get('reason', ''),
                    'position_size': decision.get('position_size'),
                    'open_positions_count': len(open_positions),
                    'market_data_summary': f"{len(market_data_list)} markets",
                    'executed': False,
                    'execution_result': None
                }
                self.decision_history.append(decision_record)

            logger.info("└─" + "─" * 76)

            # Execute decisions (clean output)
            logger.info("")
            logger.info("┌─ EXECUTION " + "─" * 64)

            decision_idx = len(self.decision_history) - len(decisions)
            for i, decision in enumerate(decisions, 1):
                action_emoji = {"BUY": "🟢", "SELL": "🔴", "CLOSE": "🔵", "NOTHING": "⚪"}.get(decision['action'], "❓")
                symbol = decision.get('symbol', 'N/A')

                if decision['action'] == "NOTHING":
                    logger.info(f"│ ⚪ [{i}] NOTHING - No action taken")
                    if decision_idx < len(self.decision_history):
                        self.decision_history[decision_idx]['executed'] = True
                        self.decision_history[decision_idx]['execution_result'] = {'success': True, 'action': 'NOTHING'}
                    decision_idx += 1
                    continue

                logger.info(f"│ {action_emoji} [{i}] {decision['action']:<8} {symbol:<8} → Executing...")

                # Inject current_price from market data into decision
                if symbol and symbol in market_data_dict:
                    decision['current_price'] = market_data_dict[symbol].get('price')

                # Add delay between orders to prevent nonce conflicts
                if i > 1:
                    await asyncio.sleep(2.0)

                # Execute via Lighter executor (async)
                result = await self.executor.execute_decision(decision)

                # Update decision record with execution result
                if decision_idx < len(self.decision_history):
                    self.decision_history[decision_idx]['executed'] = True
                    self.decision_history[decision_idx]['execution_result'] = result
                decision_idx += 1

                if result.get('success'):
                    logger.info(f"│     ✅ Success: {result['action']} {symbol}")
                else:
                    logger.info(f"│     ❌ Failed: {result.get('error', 'Unknown error')}")

            logger.info("└─" + "─" * 76)

            # Cycle summary with completion timestamp
            cycle_end = datetime.now()
            cycle_duration = (cycle_end - current_time).total_seconds()
            logger.info("")
            logger.info("╔" + "═" * 78 + "╗")
            logger.info(f"║ ✅ CYCLE COMPLETE ({cycle_end.strftime('%H:%M:%S')}) | Duration: {cycle_duration:.1f}s | Cost: ${total_cost:.4f} | Daily: ${self.llm_agent.get_daily_spend():.4f}/$10 ║")
            logger.info("╚" + "═" * 78 + "╝")
            logger.info("")

        except Exception as e:
            logger.error("")
            logger.error("╔" + "═" * 78 + "╗")
            logger.error(f"║ ❌ CYCLE ERROR: {str(e):<65} ║")
            logger.error("╚" + "═" * 78 + "╝")
            logger.error("", exc_info=True)

    async def run(self):
        """Main bot loop - mirrors Pacifica bot"""
        logger.info("Starting Lighter Trading Bot main loop")
        logger.info(f"Check interval: {self.check_interval} seconds ({self.check_interval // 60} minutes)")
        
        prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
        logger.info(f"📝 Active Prompt Version: {prompt_version}")
        logger.info(f"Position size: ${self.position_size}")

        try:
            while True:
                await self.run_once()

                # Calculate and display next cycle time
                next_cycle_time = datetime.now() + timedelta(seconds=self.check_interval)
                logger.info("")
                logger.info("╔" + "═" * 78 + "╗")
                logger.info(f"║ ⏰ NEXT CYCLE AT: {next_cycle_time.strftime('%Y-%m-%d %H:%M:%S')} (in {self.check_interval}s / {self.check_interval//60}min){'':>16} ║")
                logger.info("╚" + "═" * 78 + "╝")
                logger.info("")

                await asyncio.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"Bot crashed: {e}", exc_info=True)


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description="Lighter Trading Bot")
    parser.add_argument("--live", action="store_true", help="Enable live trading (default: dry-run)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry run mode (no real trades)")
    parser.add_argument("--once", action="store_true", help="Run once and exit (for testing)")
    parser.add_argument("--interval", type=int, default=300, help="Check interval in seconds (default: 300 = 5 min)")

    # V4 strategy parameters - momentum-based with longer holds
    parser.add_argument("--max-position-age", type=int, default=240,
                        help="Maximum position age in minutes before auto-close (default: 240 = 4h, allows winners to run)")
    parser.add_argument("--favor-zk-zec", action="store_true",
                        help="Enable ZK/ZEC position size multipliers (default: disabled - proven losers with 35.7%% and 34.5%% WR)")

    args = parser.parse_args()

    # Determine mode
    if args.live:
        dry_run = False
        logger.warning("⚠️  LIVE TRADING MODE ENABLED ⚠️")
    else:
        dry_run = True
        logger.info("✅ Dry-run mode (no real trades)")

    # Get API keys from environment
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(dotenv_path=env_path, override=True)
    
    cambrian_api_key = os.getenv("CAMBRIAN_API_KEY")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_KEY")
    lighter_private_key = os.getenv("LIGHTER_PRIVATE_KEY") or os.getenv("LIGHTER_API_KEY_PRIVATE")
    lighter_account_index = int(os.getenv("LIGHTER_ACCOUNT_INDEX", "341823"))
    lighter_api_key_index = int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))

    if not all([cambrian_api_key, deepseek_api_key, lighter_private_key]):
        logger.error("Missing required environment variables:")
        logger.error("  - CAMBRIAN_API_KEY")
        logger.error("  - DEEPSEEK_API_KEY or DEEPSEEK_KEY")
        logger.error("  - LIGHTER_PRIVATE_KEY or LIGHTER_API_KEY_PRIVATE")
        sys.exit(1)

    # Initialize bot
    bot = LighterTradingBot(
        cambrian_api_key=cambrian_api_key,
        deepseek_api_key=deepseek_api_key,
        lighter_private_key=lighter_private_key,
        lighter_account_index=lighter_account_index,
        lighter_api_key_index=lighter_api_key_index,
        dry_run=dry_run,
        check_interval=args.interval,
        max_position_age_minutes=args.max_position_age,  # V4 strategy: 240 min default
        favor_zk_zec=args.favor_zk_zec  # V4 strategy: disabled by default
    )

    # Run
    if args.once:
        logger.info("Running single decision cycle...")
        asyncio.run(bot.run_once())
    else:
        asyncio.run(bot.run())


if __name__ == "__main__":
    main()

