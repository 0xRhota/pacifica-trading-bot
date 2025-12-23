"""
Swing Trading Exit Rules
Based on 2025-11-27 research findings

Key differences from scalping:
- 3:1 R/R ratio (15% TP, 5% SL)
- Minimum 4 hour hold time
- Only exit on setup invalidation OR target/stop hit
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SwingExitRules:
    """
    Enforces swing trading exit rules based on research findings.

    Key rules:
    1. 3:1 Reward/Risk: +15% target, -5% stop
    2. Minimum 4 hour hold (trades need time to develop)
    3. Maximum 96 hour hold (opportunity cost)
    4. Technical invalidation (trend reversal)
    """

    def __init__(
        self,
        take_profit_pct: float = 15.0,
        stop_loss_pct: float = 5.0,
        min_hold_hours: float = 4.0,
        max_hold_hours: float = 96.0
    ):
        """
        Initialize swing exit rules

        Args:
            take_profit_pct: Take profit percentage (default: 15.0)
            stop_loss_pct: Stop loss percentage (default: 5.0)
            min_hold_hours: Minimum hours to hold (default: 4.0)
            max_hold_hours: Maximum hours to hold (default: 96.0)
        """
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.min_hold_hours = min_hold_hours
        self.max_hold_hours = max_hold_hours

        # Calculate required win rate for breakeven
        # Win rate = SL / (SL + TP) = 5 / (5 + 15) = 25%
        self.required_win_rate = stop_loss_pct / (stop_loss_pct + take_profit_pct)

        logger.info(f"SwingExitRules initialized:")
        logger.info(f"  Take Profit: +{take_profit_pct}%")
        logger.info(f"  Stop Loss: -{stop_loss_pct}%")
        logger.info(f"  R/R Ratio: {take_profit_pct/stop_loss_pct:.1f}:1")
        logger.info(f"  Required Win Rate: {self.required_win_rate*100:.1f}%")
        logger.info(f"  Min Hold: {min_hold_hours}h, Max Hold: {max_hold_hours}h")

    def get_hold_time(self, tracker_data: Optional[Dict]) -> Optional[float]:
        """Get hold time in hours from tracker data"""
        if not tracker_data:
            return None

        timestamp_str = tracker_data.get('timestamp')
        if not timestamp_str:
            return None

        try:
            entry_time = datetime.fromisoformat(timestamp_str)
            hold_time = datetime.now() - entry_time
            return hold_time.total_seconds() / 3600
        except Exception:
            return None

    def check_should_force_close(
        self,
        position: Dict,
        market_data: Dict,
        tracker_data: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Check if position should be force-closed by swing trading rules

        Args:
            position: Position dict with symbol, side, entry_price, pnl_pct
            market_data: Market data dict with RSI, MACD, SMA20, SMA50
            tracker_data: Trade tracker data with timestamp

        Returns:
            (should_close: bool, reason: str)
        """
        symbol = position.get('symbol', 'UNKNOWN')
        side = position.get('side', 'UNKNOWN')

        # Get P/L percentage (convert from decimal if needed)
        pnl_pct = position.get('pnl_pct', 0)
        if isinstance(pnl_pct, float) and abs(pnl_pct) < 1:
            pnl_pct = pnl_pct * 100  # Convert decimal to percentage

        # Get hold time
        hold_hours = self.get_hold_time(tracker_data)

        # RULE 1: Take Profit (+15%)
        if pnl_pct >= self.take_profit_pct:
            logger.info(f"🎯 SWING RULE: {symbol} hit +{self.take_profit_pct}% target ({pnl_pct:+.2f}%)")
            return True, f"Take profit +{self.take_profit_pct}% reached ({pnl_pct:+.2f}%)"

        # RULE 2: Stop Loss (-5%)
        if pnl_pct <= -self.stop_loss_pct:
            logger.info(f"🛑 SWING RULE: {symbol} hit -{self.stop_loss_pct}% stop ({pnl_pct:+.2f}%)")
            return True, f"Stop loss -{self.stop_loss_pct}% triggered ({pnl_pct:+.2f}%)"

        # RULE 3: Maximum hold time (96 hours / 4 days)
        if hold_hours and hold_hours >= self.max_hold_hours:
            logger.info(f"⏰ SWING RULE: {symbol} exceeded {self.max_hold_hours}h hold ({hold_hours:.1f}h)")
            return True, f"Max hold time {self.max_hold_hours}h exceeded ({hold_hours:.1f}h)"

        # RULE 4: Trend Reversal (setup invalidation)
        if market_data:
            sma20 = market_data.get('sma20', 0)
            sma50 = market_data.get('sma50', 0)
            rsi = market_data.get('rsi', 50)
            macd = market_data.get('macd', 0)

            # Only check trend reversal after minimum hold time
            if hold_hours and hold_hours >= self.min_hold_hours:

                # For LONGS: Exit if trend reverses to downtrend
                if side == 'LONG' and sma20 and sma50:
                    if sma20 < sma50 and macd < 0:
                        logger.info(f"📉 SWING RULE: {symbol} LONG trend reversal (SMA20 < SMA50, MACD {macd:.1f})")
                        return True, f"Trend reversal: SMA20 < SMA50, MACD bearish"

                # For SHORTS: Exit if trend reverses to uptrend
                if side == 'SHORT' and sma20 and sma50:
                    if sma20 > sma50 and macd > 0:
                        logger.info(f"📈 SWING RULE: {symbol} SHORT trend reversal (SMA20 > SMA50, MACD {macd:.1f})")
                        return True, f"Trend reversal: SMA20 > SMA50, MACD bullish"

        return False, ""

    def should_prevent_close(
        self,
        tracker_data: Dict,
        pnl_pct: float
    ) -> Tuple[bool, str]:
        """
        Check if position should be PREVENTED from closing
        (hasn't hit min hold time AND not at target/stop)

        This prevents LLM from closing trades too early.

        Args:
            tracker_data: Trade tracker data with timestamp
            pnl_pct: Current P&L percentage

        Returns:
            (should_prevent: bool, reason: str)
        """
        # Get hold time
        hold_hours = self.get_hold_time(tracker_data)

        if hold_hours is None:
            return False, ""

        # If under min hold time AND not at target/stop, prevent closing
        if hold_hours < self.min_hold_hours:
            # Allow closing if at target or stop
            if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct:
                return False, ""

            remaining = self.min_hold_hours - hold_hours
            logger.info(f"🔒 PREVENT CLOSE: Minimum hold not met ({hold_hours:.1f}h < {self.min_hold_hours}h)")
            return True, f"Minimum hold time: {remaining:.1f}h remaining"

        return False, ""

    def get_position_status(
        self,
        position: Dict,
        market_data: Dict,
        tracker_data: Optional[Dict] = None
    ) -> Dict:
        """
        Get detailed status of a position for logging/display

        Returns dict with:
        - symbol, side, pnl_pct
        - hold_hours
        - distance_to_tp, distance_to_sl
        - trend_aligned (bool)
        - status (healthy, warning, critical)
        """
        symbol = position.get('symbol', 'UNKNOWN')
        side = position.get('side', 'UNKNOWN')

        pnl_pct = position.get('pnl_pct', 0)
        if isinstance(pnl_pct, float) and abs(pnl_pct) < 1:
            pnl_pct = pnl_pct * 100

        hold_hours = self.get_hold_time(tracker_data) or 0

        distance_to_tp = self.take_profit_pct - pnl_pct
        distance_to_sl = pnl_pct + self.stop_loss_pct

        # Check trend alignment
        trend_aligned = True
        if market_data:
            sma20 = market_data.get('sma20', 0)
            sma50 = market_data.get('sma50', 0)
            if sma20 and sma50:
                if side == 'LONG' and sma20 < sma50:
                    trend_aligned = False
                elif side == 'SHORT' and sma20 > sma50:
                    trend_aligned = False

        # Determine status
        if pnl_pct >= self.take_profit_pct * 0.7:  # >70% to target
            status = "near_target"
        elif pnl_pct <= -self.stop_loss_pct * 0.7:  # >70% to stop
            status = "critical"
        elif not trend_aligned:
            status = "warning"
        else:
            status = "healthy"

        return {
            "symbol": symbol,
            "side": side,
            "pnl_pct": pnl_pct,
            "hold_hours": hold_hours,
            "distance_to_tp": distance_to_tp,
            "distance_to_sl": distance_to_sl,
            "trend_aligned": trend_aligned,
            "status": status
        }
