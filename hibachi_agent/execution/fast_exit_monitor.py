"""
Fast Exit Monitor for Hibachi Bot
Based on 2025-11-28 optimization request

PURPOSE:
- Check positions every 30 seconds (vs 5 min LLM cycles)
- Exit immediately when TP/SL hit
- NO LLM calls = FREE (just price API calls)
- Designed to capture quick moves that would otherwise be missed

ARCHITECTURE:
- Runs as asyncio task alongside main bot loop
- Uses existing StrategyAExitRules for exit logic
- Only checks prices and executes closes
- Does NOT make new entries (that's the LLM's job)

COST IMPACT:
- LLM: $0 (no LLM calls)
- API: Negligible (price fetches only)
- Total: ~$0/day additional cost

LATENCY IMPROVEMENT:
- Before: 0-300s delay to exit (5 min average)
- After: 0-30s delay to exit (15s average)
- 10x faster reaction to TP/SL hits
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FastExitMonitor:
    """
    Fast exit monitoring loop - checks positions every 30 seconds

    Separates exit monitoring from LLM decision cycles for faster reactions.
    NO LLM calls = FREE operation.
    """

    MONITOR_NAME = "FAST_EXIT_MONITOR_V1"
    CHECK_INTERVAL_SECONDS = 30  # Check every 30 seconds

    def __init__(
        self,
        sdk,                    # HibachiSDK for price fetches
        executor,               # HibachiTradeExecutor for closing positions
        exit_rules,             # StrategyAExitRules (or B) for exit logic
        trade_tracker,          # TradeTracker for position data
        enabled: bool = True,
        exit_callback=None      # Optional callback for recording exits (for self-improving learning)
    ):
        """
        Initialize fast exit monitor

        Args:
            sdk: DEX SDK for price fetches
            executor: Trade executor for closing positions
            exit_rules: Strategy exit rules (A or B)
            trade_tracker: Trade tracker for position history
            enabled: Whether monitoring is active (default: True)
            exit_callback: Optional callback(symbol, exit_price, pnl_usd) for learning systems
        """
        self.sdk = sdk
        self.executor = executor
        self.exit_rules = exit_rules
        self.tracker = trade_tracker
        self.enabled = enabled
        self.exit_callback = exit_callback

        # Statistics
        self.checks_performed = 0
        self.exits_triggered = 0
        self.last_check_time = None
        self.running = False

        logger.info("=" * 60)
        logger.info(f"FAST EXIT MONITOR: {self.MONITOR_NAME}")
        logger.info(f"  Check Interval: {self.CHECK_INTERVAL_SECONDS}s")
        logger.info(f"  Status: {'ENABLED' if enabled else 'DISABLED'}")
        logger.info(f"  Cost: $0 (no LLM calls)")
        logger.info("=" * 60)

    async def check_positions_once(self) -> List[Dict]:
        """
        Single check of all positions against exit rules

        Returns:
            List of positions that were closed
        """
        closed_positions = []

        try:
            # Fetch current positions
            positions = await self.executor._fetch_open_positions()

            if not positions:
                return closed_positions

            for position in positions:
                symbol = position.get('symbol')
                quantity = float(position.get('quantity', 0))

                if quantity == 0:
                    continue

                direction = position.get('direction', 'Long')
                side = 'LONG' if direction == 'Long' else 'SHORT'

                # Get tracker data for entry price
                tracker_data = self.tracker.get_open_trade_for_symbol(symbol)
                entry_price = tracker_data.get('entry_price', 0) if tracker_data else 0

                if not entry_price or entry_price <= 0:
                    continue

                # Fetch current price
                current_price = await self.sdk.get_price(symbol)
                if not current_price:
                    continue

                # Calculate P/L percentage
                if side == 'LONG':
                    pnl_pct = ((current_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl_pct = ((entry_price - current_price) / entry_price) * 100

                # Build position dict for exit rules
                position_for_rules = {
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'pnl_pct': pnl_pct / 100  # Convert to decimal for rules
                }

                # Check exit rules (TP/SL/trailing/time)
                should_close, reason = self.exit_rules.check_should_force_close(
                    position_for_rules,
                    {},  # No market data needed for basic TP/SL
                    tracker_data
                )

                if should_close:
                    logger.info(f"⚡ [FAST-EXIT] {symbol} triggered: {reason}")
                    logger.info(f"   Entry: ${entry_price:.4f} → Current: ${current_price:.4f}")
                    logger.info(f"   P/L: {pnl_pct:+.2f}%")

                    # Execute close immediately
                    close_decision = {
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'reasoning': f"FAST-EXIT: {reason}",
                        'confidence': 1.0
                    }

                    result = await self.executor.execute_decision(close_decision)

                    if result.get('success'):
                        logger.info(f"   ✅ Fast exit executed successfully")
                        self.exits_triggered += 1

                        # Calculate PnL in USD (estimate based on tracker notional)
                        notional = tracker_data.get('notional', 0) if tracker_data else 0
                        pnl_usd = notional * (pnl_pct / 100) if notional else None

                        closed_positions.append({
                            'symbol': symbol,
                            'side': side,
                            'pnl_pct': pnl_pct,
                            'pnl_usd': pnl_usd,
                            'reason': reason,
                            'price': current_price
                        })

                        # Record exit for self-improving learning system
                        if self.exit_callback:
                            try:
                                self.exit_callback(
                                    symbol=symbol,
                                    exit_price=current_price,
                                    pnl_usd=pnl_usd
                                )
                                logger.info(f"   📚 Recorded exit for learning system")
                            except Exception as cb_err:
                                logger.error(f"   ⚠️ Exit callback error: {cb_err}")

                        # Unregister from exit rules tracking
                        self.exit_rules.unregister_position(symbol)
                    else:
                        logger.error(f"   ❌ Fast exit failed: {result.get('error')}")
                else:
                    # Log position status at debug level
                    logger.debug(f"[FAST-EXIT] {symbol}: P/L {pnl_pct:+.2f}% - holding")

        except Exception as e:
            logger.error(f"[FAST-EXIT] Error checking positions: {e}")

        return closed_positions

    async def run(self):
        """
        Continuous monitoring loop - runs every 30 seconds

        This runs as a separate asyncio task from the main bot loop.
        """
        if not self.enabled:
            logger.info("[FAST-EXIT] Monitor disabled - not starting")
            return

        self.running = True
        logger.info(f"🚀 [FAST-EXIT] Starting monitor loop (every {self.CHECK_INTERVAL_SECONDS}s)")

        try:
            while self.running:
                self.checks_performed += 1
                self.last_check_time = datetime.now()

                # Log less frequently to avoid spam
                if self.checks_performed % 10 == 1:  # Every 5 minutes
                    logger.info(f"[FAST-EXIT] Check #{self.checks_performed} | Exits triggered: {self.exits_triggered}")

                closed = await self.check_positions_once()

                if closed:
                    logger.info(f"[FAST-EXIT] Closed {len(closed)} position(s) this check")

                await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            logger.info("[FAST-EXIT] Monitor loop cancelled")
        except Exception as e:
            logger.error(f"[FAST-EXIT] Fatal error in monitor loop: {e}")
        finally:
            self.running = False

    def stop(self):
        """Stop the monitoring loop"""
        self.running = False
        logger.info("[FAST-EXIT] Monitor stopped")

    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        return {
            "monitor": self.MONITOR_NAME,
            "enabled": self.enabled,
            "running": self.running,
            "checks_performed": self.checks_performed,
            "exits_triggered": self.exits_triggered,
            "check_interval_seconds": self.CHECK_INTERVAL_SECONDS,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None
        }

    def log_stats(self):
        """Log current statistics"""
        stats = self.get_stats()
        logger.info("-" * 40)
        logger.info(f"[FAST-EXIT STATS]")
        logger.info(f"  Status: {'Running' if stats['running'] else 'Stopped'}")
        logger.info(f"  Checks: {stats['checks_performed']}")
        logger.info(f"  Exits: {stats['exits_triggered']}")
        logger.info(f"  Last Check: {stats['last_check_time'] or 'Never'}")
        logger.info("-" * 40)
