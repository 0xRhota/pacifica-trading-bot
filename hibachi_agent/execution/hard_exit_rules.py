"""
Hard Exit Rules - Overrides LLM discretion

These rules FORCE position exits regardless of LLM opinion.
Goal: Prevent LLM's risk aversion from closing winners too early.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class HardExitRules:
    """
    Enforces hard exit rules that override LLM decisions.

    Rules:
    1. Minimum hold time: 2 hours (prevent quick exits)
    2. Profit target: +2% (force take profit)
    3. Stop loss: -1.5% (force cut losses)
    4. Technical invalidation: RSI/MACD reversal (exit if setup breaks)
    """

    def __init__(
        self,
        min_hold_hours: float = 2.0,
        profit_target_pct: float = 2.0,
        stop_loss_pct: float = 1.5
    ):
        """
        Initialize hard exit rules

        Args:
            min_hold_hours: Minimum hours to hold (default: 2.0)
            profit_target_pct: Profit target percentage (default: 2.0)
            stop_loss_pct: Stop loss percentage (default: 1.5)
        """
        self.min_hold_hours = min_hold_hours
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct

    def check_should_force_close(
        self,
        position: Dict,
        market_data: Dict,
        tracker_data: Optional[Dict] = None
    ) -> tuple[bool, str]:
        """
        Check if position should be force-closed by hard rules

        Args:
            position: Position dict with symbol, side, entry_price, pnl_pct
            market_data: Market data dict with RSI, MACD, etc.
            tracker_data: Trade tracker data with timestamp

        Returns:
            (should_close: bool, reason: str)
        """
        symbol = position.get('symbol', 'UNKNOWN')
        side = position.get('side', 'UNKNOWN')
        pnl_pct = position.get('pnl_pct', 0) * 100 if position.get('pnl_pct') else 0

        # Get entry time from tracker
        entry_time = None
        if tracker_data:
            timestamp_str = tracker_data.get('timestamp')
            if timestamp_str:
                try:
                    entry_time = datetime.fromisoformat(timestamp_str)
                except:
                    pass

        # RULE 1: Profit target (+2%)
        if pnl_pct >= self.profit_target_pct:
            logger.info(f"🎯 HARD RULE: {symbol} hit +{self.profit_target_pct}% target ({pnl_pct:+.2f}%)")
            return True, f"Profit target +{self.profit_target_pct}% reached ({pnl_pct:+.2f}%)"

        # RULE 2: Stop loss (-1.5%)
        if pnl_pct <= -self.stop_loss_pct:
            logger.info(f"🛑 HARD RULE: {symbol} hit -{self.stop_loss_pct}% stop ({pnl_pct:+.2f}%)")
            return True, f"Stop loss -{self.stop_loss_pct}% triggered ({pnl_pct:+.2f}%)"

        # RULE 3: Minimum hold time (2 hours)
        if entry_time:
            hold_time = datetime.now() - entry_time
            hold_hours = hold_time.total_seconds() / 3600

            # If under min hold time AND not at target/stop, prevent LLM from closing
            if hold_hours < self.min_hold_hours:
                # This rule PREVENTS closing, not forces it
                # We'll handle this in the caller
                pass

        # RULE 4: Technical invalidation
        # Check if the technical setup that justified entry has broken down
        if market_data:
            rsi = market_data.get('rsi', 50)
            macd = market_data.get('macd', 0)

            # For longs: Exit if RSI drops below 30 AND MACD turns negative
            if side == 'LONG':
                if rsi < 30 and macd < 0:
                    logger.info(f"⚠️  HARD RULE: {symbol} LONG technical invalidation (RSI {rsi:.0f}, MACD {macd:.1f})")
                    return True, f"Technical invalidation: RSI {rsi:.0f} oversold + MACD {macd:.1f} bearish"

            # For shorts: Exit if RSI rises above 70 AND MACD turns positive
            elif side == 'SHORT':
                if rsi > 70 and macd > 0:
                    logger.info(f"⚠️  HARD RULE: {symbol} SHORT technical invalidation (RSI {rsi:.0f}, MACD {macd:.1f})")
                    return True, f"Technical invalidation: RSI {rsi:.0f} overbought + MACD {macd:.1f} bullish"

        return False, ""

    def should_prevent_close(
        self,
        tracker_data: Dict,
        pnl_pct: float
    ) -> tuple[bool, str]:
        """
        Check if position should be PREVENTED from closing
        (e.g., hasn't hit min hold time and not at target/stop)

        Args:
            tracker_data: Trade tracker data with timestamp
            pnl_pct: Current P&L percentage

        Returns:
            (should_prevent: bool, reason: str)
        """
        # DISABLED: No minimum hold enforcement - let LLM exit when setup breaks
        return False, ""
