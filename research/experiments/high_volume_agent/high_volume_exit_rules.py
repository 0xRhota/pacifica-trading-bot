"""
High Volume Exit Rules
Based on Qwen analysis 2025-11-27

Key difference from swing trading:
- 4:1 R/R (4% TP, 1% SL) instead of 3:1 (15% TP, 5% SL)
- TIME-BASED EXIT: Close after 1 hour regardless of P/L
- This is the secret to maintaining high volume without bleeding fees
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class HighVolumeExitRules:
    """
    Exit rules optimized for high volume trading (10-20 trades/day)

    Key rules:
    1. Take Profit: +4% (hit more often than swing's 15%)
    2. Stop Loss: -1% (tight, cut fast)
    3. TIME EXIT: Close after 1 hour (THE KEY TO HIGH VOLUME)
    """

    def __init__(
        self,
        take_profit_pct: float = 4.0,
        stop_loss_pct: float = 1.0,
        time_exit_minutes: int = 60,
        min_hold_minutes: int = 5
    ):
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.time_exit_minutes = time_exit_minutes
        self.min_hold_minutes = min_hold_minutes

        # Calculate required win rate
        # EV = W * (TP - fee) - (1-W) * (SL + fee)
        # At breakeven: W = (SL + fee) / (TP + SL)
        fee = 0.1  # 0.1% per trade
        self.required_win_rate = (stop_loss_pct + fee) / (take_profit_pct + stop_loss_pct)

        logger.info(f"HighVolumeExitRules initialized:")
        logger.info(f"  Take Profit: +{take_profit_pct}%")
        logger.info(f"  Stop Loss: -{stop_loss_pct}%")
        logger.info(f"  R/R Ratio: {take_profit_pct/stop_loss_pct:.1f}:1")
        logger.info(f"  Required Win Rate: {self.required_win_rate*100:.1f}%")
        logger.info(f"  Time Exit: {time_exit_minutes} minutes")
        logger.info(f"  Min Hold: {min_hold_minutes} minutes")

    def get_hold_minutes(self, tracker_data: Optional[Dict]) -> Optional[float]:
        """Get hold time in minutes from tracker data"""
        if not tracker_data:
            return None

        timestamp_str = tracker_data.get('timestamp')
        if not timestamp_str:
            return None

        try:
            entry_time = datetime.fromisoformat(timestamp_str)
            hold_time = datetime.now() - entry_time
            return hold_time.total_seconds() / 60
        except Exception:
            return None

    def check_should_force_close(
        self,
        position: Dict,
        market_data: Dict,
        tracker_data: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Check if position should be force-closed by high volume rules

        Priority order:
        1. Take Profit (+4%)
        2. Stop Loss (-1%)
        3. Time Exit (1 hour)

        Args:
            position: Position dict with symbol, side, entry_price, pnl_pct
            market_data: Market data dict (not used for exits, but kept for interface)
            tracker_data: Trade tracker data with timestamp

        Returns:
            (should_close: bool, reason: str)
        """
        symbol = position.get('symbol', 'UNKNOWN')
        side = position.get('side', 'UNKNOWN')

        # Get P/L percentage
        pnl_pct = position.get('pnl_pct', 0)
        if isinstance(pnl_pct, float) and abs(pnl_pct) < 1:
            pnl_pct = pnl_pct * 100  # Convert decimal to percentage

        # Get hold time
        hold_minutes = self.get_hold_minutes(tracker_data)

        # RULE 1: Take Profit (+4%)
        if pnl_pct >= self.take_profit_pct:
            logger.info(f"🎯 HIGH VOL: {symbol} hit +{self.take_profit_pct}% TP ({pnl_pct:+.2f}%)")
            return True, f"Take profit +{self.take_profit_pct}% hit ({pnl_pct:+.2f}%)"

        # RULE 2: Stop Loss (-1%)
        if pnl_pct <= -self.stop_loss_pct:
            logger.info(f"🛑 HIGH VOL: {symbol} hit -{self.stop_loss_pct}% SL ({pnl_pct:+.2f}%)")
            return True, f"Stop loss -{self.stop_loss_pct}% hit ({pnl_pct:+.2f}%)"

        # RULE 3: Time Exit (1 hour) - THE KEY TO HIGH VOLUME
        if hold_minutes and hold_minutes >= self.time_exit_minutes:
            logger.info(f"⏰ HIGH VOL: {symbol} hit {self.time_exit_minutes}min time limit ({hold_minutes:.0f}min, P/L: {pnl_pct:+.2f}%)")
            return True, f"Time exit {self.time_exit_minutes}min ({hold_minutes:.0f}min, P/L: {pnl_pct:+.2f}%)"

        return False, ""

    def should_prevent_close(
        self,
        tracker_data: Dict,
        pnl_pct: float
    ) -> Tuple[bool, str]:
        """
        Check if position should be PREVENTED from closing
        (for high volume, we want quick exits so this is rarely used)

        Only prevent if:
        - Hold time < min_hold_minutes (5 min)
        - AND not at TP or SL

        Args:
            tracker_data: Trade tracker data with timestamp
            pnl_pct: Current P&L percentage

        Returns:
            (should_prevent: bool, reason: str)
        """
        hold_minutes = self.get_hold_minutes(tracker_data)

        if hold_minutes is None:
            return False, ""

        # If under min hold AND not at target/stop, prevent LLM from closing
        if hold_minutes < self.min_hold_minutes:
            # Allow if at TP or SL
            if pnl_pct >= self.take_profit_pct or pnl_pct <= -self.stop_loss_pct:
                return False, ""

            remaining = self.min_hold_minutes - hold_minutes
            logger.debug(f"🔒 Min hold not met ({hold_minutes:.1f}min < {self.min_hold_minutes}min)")
            return True, f"Min hold: {remaining:.1f}min remaining"

        return False, ""

    def get_position_status(
        self,
        position: Dict,
        tracker_data: Optional[Dict] = None
    ) -> Dict:
        """
        Get detailed status for logging/display

        Returns dict with:
        - symbol, side, pnl_pct
        - hold_minutes
        - time_remaining (until forced time exit)
        - distance_to_tp, distance_to_sl
        - status (healthy, near_target, near_stop, near_timeout)
        """
        symbol = position.get('symbol', 'UNKNOWN')
        side = position.get('side', 'UNKNOWN')

        pnl_pct = position.get('pnl_pct', 0)
        if isinstance(pnl_pct, float) and abs(pnl_pct) < 1:
            pnl_pct = pnl_pct * 100

        hold_minutes = self.get_hold_minutes(tracker_data) or 0
        time_remaining = max(0, self.time_exit_minutes - hold_minutes)

        distance_to_tp = self.take_profit_pct - pnl_pct
        distance_to_sl = pnl_pct + self.stop_loss_pct

        # Determine status
        if pnl_pct >= self.take_profit_pct * 0.75:  # >75% to target
            status = "near_target"
        elif pnl_pct <= -self.stop_loss_pct * 0.75:  # >75% to stop
            status = "near_stop"
        elif time_remaining <= 10:  # <10 min to timeout
            status = "near_timeout"
        else:
            status = "healthy"

        return {
            "symbol": symbol,
            "side": side,
            "pnl_pct": pnl_pct,
            "hold_minutes": hold_minutes,
            "time_remaining": time_remaining,
            "distance_to_tp": distance_to_tp,
            "distance_to_sl": distance_to_sl,
            "status": status
        }


class DailyTracker:
    """Track daily trading limits"""

    def __init__(self, max_trades: int = 20, max_loss_pct: float = 2.0):
        self.max_trades = max_trades
        self.max_loss_pct = max_loss_pct
        self.reset()

    def reset(self):
        """Reset daily counters"""
        self.trades_today = 0
        self.daily_pnl_pct = 0.0
        self.last_reset = datetime.now().date()

    def _check_reset(self):
        """Reset if new day"""
        if datetime.now().date() != self.last_reset:
            self.reset()

    def record_trade(self, pnl_pct: float):
        """Record a completed trade"""
        self._check_reset()
        self.trades_today += 1
        self.daily_pnl_pct += pnl_pct
        logger.info(f"📊 Daily: {self.trades_today}/{self.max_trades} trades, {self.daily_pnl_pct:+.2f}% P/L")

    def can_trade(self) -> Tuple[bool, str]:
        """Check if we can open new trades"""
        self._check_reset()

        if self.trades_today >= self.max_trades:
            return False, f"Max trades ({self.max_trades}) reached for today"

        if self.daily_pnl_pct <= -self.max_loss_pct:
            return False, f"Max daily loss ({self.max_loss_pct}%) reached"

        return True, ""

    def get_status(self) -> Dict:
        """Get daily status"""
        self._check_reset()
        return {
            "trades_today": self.trades_today,
            "trades_remaining": self.max_trades - self.trades_today,
            "daily_pnl_pct": self.daily_pnl_pct,
            "can_trade": self.can_trade()[0]
        }
