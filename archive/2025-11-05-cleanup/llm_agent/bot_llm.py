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
from typing import Optional, List, Dict
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_agent.data import MarketDataAggregator
from llm_agent.llm import LLMTradingAgent
from llm_agent.execution import TradeExecutor
from trade_tracker import TradeTracker
from dexes.pacifica.pacifica_sdk import PacificaSDK
from config import GlobalConfig

# Load environment variables from project root
project_root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path=project_root_env, override=True)

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
logger.info(f"✅ Loaded environment variables from: {project_root_env}")


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
        max_positions: int = 15  # Increased from 3 to allow more freedom
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

        # Track last deep research cycle (hourly)
        self.last_deep_research_time = datetime.now()
        self.deep_research_interval = 3600  # 1 hour in seconds
        
        # Track decisions for hourly review
        self.decision_history = []  # List of decision dicts with timestamp, reasoning, outcome

        logger.info("✅ LLM Trading Bot initialized successfully")
        
        # Log prompt version
        prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
        logger.info(f"📝 Active Prompt Version: {prompt_version}")

    def _fetch_account_balance(self) -> Optional[float]:
        """
        Fetch account balance from Pacifica API
        
        Returns:
            Account balance in USD, or None if fetch fails
        """
        try:
            import requests
            
            # Try to get account value from positions endpoint (it includes account value in errors)
            # Or use account endpoint if available
            response = requests.get(
                f"https://api.pacifica.fi/api/v1/positions",
                params={"account": self.pacifica_account},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Look for account value or balance in response
                # API structure may vary, try common fields
                if isinstance(data, list):
                    # If positions list, try to get account info from elsewhere
                    # For now, return None and let trade executor fetch it
                    return None
                elif isinstance(data, dict):
                    balance = data.get('available_to_spend') or data.get('balance') or data.get('account_value')
                    if balance:
                        return float(balance)
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not fetch account balance: {e}")
            return None

    def _get_market_summary_for_decision(self, market_data: dict, symbol: Optional[str]) -> str:
        """Get minimal market context for a decision (just the symbol's key metrics)"""
        if not symbol or symbol not in market_data:
            return "N/A"
        
        data = market_data[symbol]
        return f"Price: ${data.get('price', 0):.4f}, RSI: {data.get('rsi', 0):.1f}, Volume: {data.get('volume_24h', 0):,.0f}"
    
    def _generate_hourly_review(self) -> str:
        """
        Generate hourly review - Python collects data, prompt guides LLM thinking
        
        Returns:
            Formatted review with decision data and sequential thinking prompts
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        # Collect decision data (Python just gathers, doesn't analyze)
        recent_decisions = [
            d for d in self.decision_history
            if datetime.fromisoformat(d['timestamp']) >= cutoff_time
        ]
        
        # Collect trade outcomes for reference (Python just gathers)
        all_trades = self.trade_tracker.get_recent_trades(hours=1, limit=100)
        closed_trades = [t for t in all_trades if t.get('status') == 'closed' and t.get('exit_timestamp')]
        open_trades = [t for t in all_trades if t.get('status') == 'open']
        
        # Build review - Data collection only, prompting does the thinking
        review = []
        review.append("=" * 80)
        review.append("🔬 HOURLY DEEP RESEARCH CYCLE - SEQUENTIAL THINKING REQUIRED")
        review.append("=" * 80)
        review.append(f"Review Period: Last 1 hour (since {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')})")
        review.append("=" * 80)
        review.append("")
        review.append("**YOUR TASK: Analyze your own decision-making using sequential thinking**")
        review.append("")
        review.append("Think step-by-step through each decision you made:")
        review.append("1. WHAT decision did you make?")
        review.append("2. WHY did you make it? (What data/pattern triggered it?)")
        review.append("3. HOW did it turn out? (What was the outcome?)")
        review.append("4. WHAT could you have done better? (Should you have held longer? Exited earlier? Not taken it?)")
        review.append("5. HOW will this change your future decisions?")
        review.append("")
        
        # YOUR DECISIONS - Raw data for LLM to analyze
        if recent_decisions:
            review.append("=" * 80)
            review.append(f"📝 YOUR DECISIONS FROM PAST HOUR ({len(recent_decisions)} total):")
            review.append("=" * 80)
            review.append("")
            
            for i, decision in enumerate(recent_decisions, 1):
                review.append(f"--- Decision #{i} ---")
                review.append(f"Time: {decision['timestamp'][:16]}")
                review.append(f"Action: {decision['action']}")
                if decision.get('symbol'):
                    review.append(f"Symbol: {decision['symbol']}")
                if decision.get('side'):
                    review.append(f"Side: {decision['side']}")
                review.append(f"Confidence: {decision.get('confidence', 0.5):.2f}")
                review.append(f"Market at Decision Time: {decision.get('market_data_summary', 'N/A')}")
                review.append(f"Open Positions: {decision.get('open_positions_count', 0)}")
                review.append(f"Your Reasoning: {decision.get('reason', 'N/A')}")
                
                exec_result = decision.get('execution_result')
                if exec_result:
                    if exec_result.get('success'):
                        review.append(f"Outcome: Executed {'(NOTHING - no action)' if decision['action'] == 'NOTHING' else 'successfully'}")
                    else:
                        review.append(f"Outcome: FAILED - {exec_result.get('error', 'Unknown')}")
                else:
                    review.append("Outcome: Not executed")
                review.append("")
        else:
            review.append("⚠️ No decisions recorded in past hour")
            review.append("")
        
        # Trade outcomes (reference data - LLM links to decisions)
        if closed_trades or open_trades:
            review.append("=" * 80)
            review.append("💰 TRADE OUTCOMES (Reference - Link these to your decisions above):")
            review.append("=" * 80)
            review.append("")
            
            if closed_trades:
                review.append("Closed Trades:")
                for trade in closed_trades:
                    symbol = trade.get('symbol', 'N/A')
                    side = (trade.get('side', 'N/A')).upper()
                    entry = trade.get('entry_price', 0)
                    exit_price = trade.get('exit_price', 0)
                    pnl = trade.get('pnl', 0) or 0
                    pnl_pct = trade.get('pnl_pct', 0) or 0
                    exit_time = trade.get('exit_timestamp', '')
                    review.append(f"  {symbol} | {side} | Entry: ${entry:.4f} → Exit: ${exit_price:.4f} | P&L: ${pnl:.2f} ({pnl_pct*100:.1f}%) | Closed: {exit_time[:16] if exit_time else 'N/A'}")
                review.append("")
            
            if open_trades:
                review.append("Currently Open:")
                for trade in open_trades:
                    symbol = trade.get('symbol', 'N/A')
                    side = (trade.get('side', 'N/A')).upper()
                    entry = trade.get('entry_price', 0)
                    entry_time = trade.get('timestamp', '')
                    review.append(f"  {symbol} | {side} | Entry: ${entry:.4f} | Opened: {entry_time[:16] if entry_time else 'N/A'}")
                review.append("")
        
        # Sequential thinking prompt - LLM does the analysis
        review.append("=" * 80)
        review.append("🧠 SEQUENTIAL THINKING - Work through this systematically:")
        review.append("=" * 80)
        review.append("")
        review.append("**STEP 1: DECISION REVIEW**")
        review.append("For each decision above, ask yourself:")
        review.append("  • What market signal did I see? (RSI level? MACD crossover? Volume spike?)")
        review.append("  • Was my reasoning logical given the data?")
        review.append("  • Did market conditions support this decision?")
        review.append("")
        review.append("**STEP 2: OUTCOME ANALYSIS**")
        review.append("For decisions that led to trades:")
        review.append("  • Did the trade work? Was my analysis correct?")
        review.append("  • Did I close too early? (Check: Did price continue in my favor after I closed?)")
        review.append("  • Did I hold too long? (Check: Could I have taken profit earlier? Did I give back gains?)")
        review.append("  • Was my confidence level accurate? (Did I over/under-estimate?)")
        review.append("")
        review.append("**STEP 3: MISSED OPPORTUNITIES**")
        review.append("For 'NOTHING' decisions:")
        review.append("  • Did I miss signals I should have acted on?")
        review.append("  • Did conditions improve after I chose NOTHING?")
        review.append("  • Am I being too conservative? Missing obvious setups?")
        review.append("")
        review.append("**STEP 4: PATTERN IDENTIFICATION**")
        review.append("Look across ALL decisions:")
        review.append("  • Pattern: Do I consistently close winners too early?")
        review.append("  • Pattern: Do I hold losers too long?")
        review.append("  • Pattern: Am I missing certain signal types? (RSI oversold? Volume spikes?)")
        review.append("  • Pattern: Do specific market conditions lead to better outcomes?")
        review.append("  • Pattern: Are my confidence levels correlated with actual success?")
        review.append("")
        review.append("**STEP 5: ADJUSTMENTS**")
        review.append("Based on your analysis above, what will you do differently in the next hour?")
        review.append("  • Should I hold positions longer? (If I'm closing winners too early)")
        review.append("  • Should I exit faster? (If I'm holding losers too long)")
        review.append("  • Should I be more aggressive? (If I'm missing opportunities)")
        review.append("  • Should I adjust confidence thresholds? (If my confidence doesn't match outcomes)")
        review.append("  • Should I look for different signals? (If certain patterns aren't working)")
        review.append("")
        review.append("=" * 80)
        review.append("**CRITICAL: Use this analysis to inform your next trading decisions.**")
        review.append("Your insights from this review should directly impact how you trade in the next hour.")
        review.append("=" * 80)
        
        return "\n".join(review)

    def _sync_tracker_with_api(self):
        """
        Sync trade tracker with actual API positions
        Closes stale tracker entries that don't exist on exchange
        """
        try:
            # Get actual API positions
            api_positions = self._fetch_open_positions()
            api_position_keys = set()
            for pos in api_positions:
                symbol = pos.get('symbol')
                side = 'buy' if pos.get('side') == 'LONG' else 'sell'
                api_position_keys.add(f"{symbol}_{side}")
            
            # Get tracker's open positions
            tracker_open = self.trade_tracker.get_open_trades()
            
            # Find stale entries (in tracker but not in API)
            stale_count = 0
            for trade in tracker_open:
                symbol = trade.get('symbol')
                side = trade.get('side')
                key = f"{symbol}_{side}"
                
                if key not in api_position_keys:
                    # Position closed on exchange but still marked open in tracker
                    order_id = trade.get('order_id')
                    if order_id:
                        # Close properly with order_id
                        self.trade_tracker.log_exit(
                            order_id=order_id,
                            exit_price=trade.get('entry_price', 0),
                            exit_reason="Closed outside bot (auto-sync)",
                            fees=0.0
                        )
                    else:
                        # Manual close (no order_id - old dry-run entries)
                        trade['status'] = 'closed'
                        trade['exit_price'] = trade.get('entry_price', 0)
                        trade['exit_timestamp'] = datetime.now().isoformat()
                        trade['exit_reason'] = 'Stale entry (auto-sync)'
                        trade['pnl'] = 0.0
                        trade['pnl_pct'] = 0.0
                        trade['fees'] = 0.0
                        self.trade_tracker._save_trades()
                    stale_count += 1
            
            if stale_count > 0:
                logger.info(f"🔄 Synced tracker: closed {stale_count} stale entries")
        except Exception as e:
            logger.warning(f"Tracker sync failed (non-critical): {e}")

    def _fetch_open_positions(self) -> List[Dict]:
        """Fetch open positions from Pacifica API"""
        try:
            import requests
            
            response = requests.get(
                f"https://api.pacifica.fi/api/v1/positions",
                params={"account": self.pacifica_account},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Pacifica API returns {"success": true, "data": [...]}
                if result.get("success") and result.get("data"):
                    positions_data = result["data"]
                elif isinstance(result, list):
                    # Handle direct list format (fallback)
                    positions_data = result
                else:
                    logger.warning(f"Unexpected positions response format: {type(result)}")
                    logger.debug(f"Response: {result}")
                    return []
                
                positions = []
                for pos in positions_data:
                    try:
                        symbol = pos.get('symbol') or pos.get('market') or 'UNKNOWN'
                        # Pacifica API returns "bid" for LONG, "ask" for SHORT
                        side_raw = pos.get('side', '').lower()
                        if side_raw == 'bid':
                            side = 'LONG'
                        elif side_raw == 'ask':
                            side = 'SHORT'
                        else:
                            side = pos.get('side', 'LONG').upper()  # Fallback
                        entry_price = float(pos.get('entry_price', 0))
                        current_price = float(pos.get('mark_price', pos.get('current_price', entry_price)))
                        # Pacifica API uses "amount" field
                        size = float(pos.get('amount', pos.get('size', pos.get('quantity', 0))))
                        
                        # Calculate P&L
                        if side == "LONG":
                            pnl = (current_price - entry_price) * size
                            pnl_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
                        else:  # SHORT
                            pnl = (entry_price - current_price) * size
                            pnl_pct = (entry_price - current_price) / entry_price if entry_price > 0 else 0
                        
                        positions.append({
                            "symbol": symbol,
                            "side": side,
                            "entry_price": entry_price,
                            "current_price": current_price,
                            "size": size,
                            "pnl": pnl,
                            "pnl_pct": pnl_pct,
                            "time_held": "N/A"  # Would need timestamp from API
                        })
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing position: {e}")
                        continue
                
                return positions
            else:
                logger.warning("Failed to fetch positions from Pacifica API")
                return []

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def run_once(self):
        """Execute one decision cycle"""

        current_time = datetime.now()
        
        # Check if it's time for hourly deep research cycle
        time_since_last_research = (current_time - self.last_deep_research_time).total_seconds()
        is_deep_research_cycle = time_since_last_research >= self.deep_research_interval

        if is_deep_research_cycle:
            logger.info("=" * 80)
            logger.info("🔬 DEEP RESEARCH CYCLE (Hourly Review)")
            logger.info("=" * 80)
            logger.info(f"Reviewing past hour: {self.last_deep_research_time.strftime('%Y-%m-%d %H:%M:%S')} to {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)
        else:
            logger.info("=" * 80)
            logger.info(f"Decision Cycle - {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)

        try:
            # Sync tracker with API positions (clean stale entries)
            self._sync_tracker_with_api()
            
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

            # Get recently closed symbols (soft warning, not hard block)
            recently_closed = self.trade_tracker.get_recently_closed_symbols(hours=2)
            if recently_closed:
                logger.info(f"⚠️ Recently closed symbols (last 2h): {recently_closed} - Will allow if high confidence")

            # Generate hourly deep research review if needed
            hourly_review = None
            if is_deep_research_cycle:
                hourly_review = self._generate_hourly_review()
                logger.info("=" * 80)
                logger.info("📊 HOURLY REVIEW SUMMARY:")
                logger.info("=" * 80)
                for line in hourly_review.split('\n')[:50]:  # Show first 50 lines
                    logger.info(f"  {line}")
                logger.info("=" * 80)
                # Update last deep research time
                self.last_deep_research_time = current_time

            # Get LLM decision (now returns list of decisions)
            logger.info("Getting trading decision from LLM...")
            
            # Fetch account balance for LLM context
            account_balance = self._fetch_account_balance()
            if account_balance:
                logger.info(f"💰 Account balance: ${account_balance:.2f}")
            
            decisions = self.llm_agent.get_trading_decision(
                aggregator=self.aggregator,
                open_positions=open_positions,
                force_macro_refresh=False,
                trade_tracker=self.trade_tracker,  # Pass trade tracker
                recently_closed_symbols=recently_closed,  # Pass recently closed symbols
                account_balance=account_balance,  # Pass account balance
                hourly_review=hourly_review  # Pass hourly review if in deep research cycle
            )

            if not decisions:
                logger.error("Failed to get decision from LLM")
                return

            # Handle multiple decisions
            if not isinstance(decisions, list):
                decisions = [decisions]  # Backward compatibility

            prompt_version = self.llm_agent.prompt_formatter.get_prompt_version()
            logger.info("=" * 80)
            logger.info(f"LLM DECISIONS ({len(decisions)} total):")
            logger.info(f"  Prompt Version: {prompt_version}")
            
            total_cost = sum(d.get('cost', 0) for d in decisions)
            
            # Track decisions for hourly review
            current_time_str = datetime.now().isoformat()
            
            for i, decision in enumerate(decisions, 1):
                logger.info(f"  Decision {i}/{len(decisions)}:")
                logger.info(f"    Action: {decision['action']}")
                if decision.get('symbol'):
                    logger.info(f"    Symbol: {decision['symbol']}")
                logger.info(f"    Confidence: {decision.get('confidence', 0.5):.2f}")
                # Log full reason (condensed on single line)
                reason = decision.get('reason', '').replace('\n', ' ').strip()
                logger.info(f"    Reason: {reason}")
                
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
                    'market_data_summary': self._get_market_summary_for_decision(market_data, decision.get('symbol')),
                    'executed': False,  # Will be updated when executed
                    'execution_result': None
                }
                self.decision_history.append(decision_record)
            
            logger.info(f"  Total Cost: ${total_cost:.4f}")
            logger.info("=" * 80)

            # Execute all decisions and track outcomes
            decision_idx = 0
            for i, decision in enumerate(decisions, 1):
                if decision['action'] == "NOTHING":
                    logger.info(f"Decision {i}/{len(decisions)}: No action (NOTHING)")
                    # Mark NOTHING decisions as executed
                    if decision_idx < len(self.decision_history):
                        self.decision_history[decision_idx]['executed'] = True
                        self.decision_history[decision_idx]['execution_result'] = {'success': True, 'action': 'NOTHING'}
                    decision_idx += 1
                    continue
                
                logger.info(f"Executing decision {i}/{len(decisions)}: {decision['action']} {decision.get('symbol', '')}...")
                result = self.executor.execute_decision(decision)

                # Update decision record with execution result
                if decision_idx < len(self.decision_history):
                    self.decision_history[decision_idx]['executed'] = True
                    self.decision_history[decision_idx]['execution_result'] = result
                    if result.get('order_id'):
                        self.decision_history[decision_idx]['order_id'] = result['order_id']
                decision_idx += 1

                if result['success']:
                    logger.info(f"✅ Execution successful: {result['action']} {result['symbol']}")
                    if result['filled_price']:
                        logger.info(f"   Filled: {result['filled_size']:.4f} @ ${result['filled_price']:.2f}")
                    # Update open_positions for next decision validation
                    if decision['action'] in ['BUY', 'SELL']:
                        open_positions.append({"symbol": decision['symbol']})
                else:
                    logger.error(f"❌ Execution failed: {result.get('error')}")

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
    parser.add_argument("--live", action="store_true", help="Enable live trading (default: dry-run)")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry run mode (no real trades)")
    parser.add_argument("--once", action="store_true", help="Run once and exit (for testing)")
    parser.add_argument("--interval", type=int, default=300, help="Check interval in seconds (default: 300 = 5 min)")

    args = parser.parse_args()

    # Determine mode
    if args.live:
        dry_run = False
        logger.warning("⚠️  LIVE TRADING MODE ENABLED ⚠️")
    else:
        dry_run = True
        logger.info("✅ Dry-run mode (no real trades)")

    # Get API keys from environment (explicitly reload to ensure we have them)
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    load_dotenv(dotenv_path=env_path, override=True)
    
    cambrian_api_key = os.getenv("CAMBRIAN_API_KEY")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_KEY")
    pacifica_api_key = os.getenv("PACIFICA_PRIVATE_KEY") or os.getenv("PACIFICA_API_KEY")
    pacifica_account = os.getenv("PACIFICA_ACCOUNT")

    if not all([cambrian_api_key, deepseek_api_key, pacifica_api_key, pacifica_account]):
        logger.error("Missing required environment variables:")
        logger.error("  - CAMBRIAN_API_KEY")
        logger.error("  - DEEPSEEK_API_KEY or DEEPSEEK_KEY")
        logger.error("  - PACIFICA_PRIVATE_KEY or PACIFICA_API_KEY")
        logger.error("  - PACIFICA_ACCOUNT")
        sys.exit(1)

    # Initialize bot
    bot = LLMTradingBot(
        cambrian_api_key=cambrian_api_key,
        deepseek_api_key=deepseek_api_key,
        pacifica_api_key=pacifica_api_key,
        pacifica_account=pacifica_account,
        dry_run=dry_run,
        check_interval=args.interval
    )

    # Run
    if args.once:
        logger.info("Running single decision cycle...")
        bot.run_once()
    else:
        bot.run()


if __name__ == "__main__":
    main()
