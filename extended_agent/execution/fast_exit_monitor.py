"""
Fast Exit Monitor for Extended Bot
Based on 2025-11-28 optimization request

PURPOSE:
- Check positions every 30 seconds (vs 5 min LLM cycles)
- Exit immediately when TP/SL/trailing stops hit
- NO LLM calls = FREE (just price API calls)
- Designed to capture quick moves that would otherwise be missed

ARCHITECTURE:
- Runs as asyncio task alongside main bot loop
- Uses existing StrategyBExitRules for exit logic (with trailing stops!)
- Only checks prices and executes closes
- Does NOT make new entries (that's the LLM's job)

STRATEGY B SPECIFIC:
- Trailing stop monitoring is CRITICAL for "let runners run"
- Need to update peak P/L tracking every 30 seconds
- Trail activation at +2%, trail distance 1.5%

COST IMPACT:
- LLM: $0 (no LLM calls)
- API: Negligible (price fetches only)
- Total: ~$0/day additional cost

LATENCY IMPROVEMENT:
- Before: 0-300s delay to exit (5 min average)
- After: 0-30s delay to exit (15s average)
- 10x faster reaction to TP/SL/trailing hits
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FastExitMonitor:
    """
    Fast exit monitoring loop for Extended - checks positions every 30 seconds

    Separates exit monitoring from LLM decision cycles for faster reactions.
    Especially important for Strategy B's trailing stops!
    NO LLM calls = FREE operation.
    """

    MONITOR_NAME = "FAST_EXIT_MONITOR_V1_EXTENDED"
    CHECK_INTERVAL_SECONDS = 30  # Check every 30 seconds

    def __init__(
        self,
        executor,               # ExtendedTradeExecutor for closing positions
        exit_rules,             # StrategyBExitRules for exit logic
        trade_tracker,          # TradeTracker for position data
        enabled: bool = True
    ):
        """
        Initialize fast exit monitor for Extended

        Args:
            executor: Trade executor for closing positions (has SDK access)
            exit_rules: Strategy B exit rules (with trailing stops)
            trade_tracker: Trade tracker for position history
            enabled: Whether monitoring is active (default: True)
        """
        self.executor = executor
        self.exit_rules = exit_rules
        self.tracker = trade_tracker
        self.enabled = enabled

        # Statistics
        self.checks_performed = 0
        self.exits_triggered = 0
        self.trailing_activations = 0
        self.last_check_time = None
        self.running = False

        logger.info("=" * 60)
        logger.info(f"FAST EXIT MONITOR: {self.MONITOR_NAME}")
        logger.info(f"  Check Interval: {self.CHECK_INTERVAL_SECONDS}s")
        logger.info(f"  Status: {'ENABLED' if enabled else 'DISABLED'}")
        logger.info(f"  Trailing Stop: Active (monitors peak P/L)")
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
                size = float(position.get('size', 0))

                if size == 0:
                    continue

                side = position.get('side', 'LONG')

                # Get entry price from tracker
                tracker_data = self.tracker.get_open_trade_for_symbol(symbol)
                entry_price = tracker_data.get('entry_price', 0) if tracker_data else 0

                if not entry_price or entry_price <= 0:
                    entry_price = position.get('entry_price', 0)

                if not entry_price or entry_price <= 0:
                    continue

                # Get current price from position data (Extended provides mark_price)
                current_price = position.get('mark_price', 0)
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

                # Track if trailing was just activated (for stats)
                was_trailing_active = self.exit_rules.trailing_active.get(symbol, False)

                # Check exit rules (TP/SL/trailing)
                # Note: check_should_force_close updates peak P/L and trailing state
                should_close, reason = self.exit_rules.check_should_force_close(
                    position_for_rules,
                    {},  # No market data needed for basic TP/SL/trailing
                    tracker_data
                )

                # Track trailing stop activations
                is_trailing_active = self.exit_rules.trailing_active.get(symbol, False)
                if not was_trailing_active and is_trailing_active:
                    self.trailing_activations += 1
                    logger.info(f"🔔 [FAST-EXIT] Trailing stop ACTIVATED for {symbol} (+{pnl_pct:.2f}%)")

                if should_close:
                    peak_pnl = self.exit_rules.position_peak_pnl.get(symbol, 0)
                    logger.info(f"⚡ [FAST-EXIT] {symbol} triggered: {reason}")
                    logger.info(f"   Entry: ${entry_price:.4f} → Current: ${current_price:.4f}")
                    logger.info(f"   P/L: {pnl_pct:+.2f}% | Peak: +{peak_pnl:.2f}%")

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
                        closed_positions.append({
                            'symbol': symbol,
                            'side': side,
                            'pnl_pct': pnl_pct,
                            'peak_pnl': peak_pnl,
                            'reason': reason,
                            'price': current_price
                        })

                        # Unregister from exit rules tracking
                        self.exit_rules.unregister_position(symbol)
                    else:
                        logger.error(f"   ❌ Fast exit failed: {result.get('error')}")
                else:
                    # Log position status at debug level with trailing info
                    peak_pnl = self.exit_rules.position_peak_pnl.get(symbol, 0)
                    trailing_status = "TRAILING" if is_trailing_active else ""
                    logger.debug(f"[FAST-EXIT] {symbol}: P/L {pnl_pct:+.2f}% | Peak +{peak_pnl:.2f}% {trailing_status}")

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
                    logger.info(
                        f"[FAST-EXIT] Check #{self.checks_performed} | "
                        f"Exits: {self.exits_triggered} | "
                        f"Trailing activations: {self.trailing_activations}"
                    )

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
            "trailing_activations": self.trailing_activations,
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
        logger.info(f"  Trailing Activations: {stats['trailing_activations']}")
        logger.info(f"  Last Check: {stats['last_check_time'] or 'Never'}")
        logger.info("-" * 40)
