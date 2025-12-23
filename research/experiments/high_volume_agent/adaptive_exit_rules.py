"""
Adaptive Exit Rules - Supports both Strategy A (Time-Capped) and Strategy B (Runners Run)
Based on Qwen analysis 2025-11-27

This module handles exits for both strategies:
- Strategy A: Hard 1-hour time limit, 4% TP, 1% SL
- Strategy B: No time limit, trailing stops, 8% TP, 1% SL
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any
from .strategies import StrategyConfig, STRATEGY_A_TIME_CAPPED, STRATEGY_B_RUNNERS_RUN

logger = logging.getLogger(__name__)


@dataclass
class PositionTracker:
    """Track a position's state for exit decisions"""
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    entry_price: float
    entry_time: datetime
    size: float
    strategy: str  # 'TIME_CAPPED' or 'RUNNERS_RUN'
    peak_pnl_pct: float = 0.0  # For trailing stop
    trailing_active: bool = False


@dataclass
class DailyTradeTracker:
    """Track daily trade count to cap volume"""
    date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    trade_count: int = 0

    def increment(self):
        """Increment trade count, reset if new day"""
        today = datetime.now().strftime('%Y-%m-%d')
        if today != self.date:
            self.date = today
            self.trade_count = 0
        self.trade_count += 1

    def can_trade(self, max_trades: int) -> bool:
        """Check if we can still trade today"""
        today = datetime.now().strftime('%Y-%m-%d')
        if today != self.date:
            return True  # New day, can trade
        return self.trade_count < max_trades


class AdaptiveExitRules:
    """
    Handles exits for both strategies with different rules:

    Strategy A (TIME_CAPPED):
    - Take profit at +4%
    - Stop loss at -1%
    - FORCE CLOSE after 1 hour
    - No trailing stop

    Strategy B (RUNNERS_RUN):
    - Take profit at +8%
    - Stop loss at -1%
    - NO time limit
    - Trailing stop: activates at +2%, trails by 1.5%
    """

    def __init__(self, strategy: StrategyConfig):
        self.strategy = strategy
        self.positions: Dict[str, PositionTracker] = {}
        self.daily_tracker = DailyTradeTracker()

    def register_position(self, symbol: str, side: str, entry_price: float, size: float):
        """Register a new position for tracking"""
        self.positions[symbol] = PositionTracker(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            entry_time=datetime.now(),
            size=size,
            strategy=self.strategy.name,
        )
        self.daily_tracker.increment()
        logger.info(f"[{self.strategy.name}] Registered {side} {symbol} @ {entry_price}")

    def unregister_position(self, symbol: str):
        """Remove a position from tracking"""
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"[{self.strategy.name}] Unregistered {symbol}")

    def check_should_force_close(
        self,
        symbol: str,
        current_price: float,
        sma20: Optional[float] = None,
        sma50: Optional[float] = None,
        macd: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Check if position should be force closed by hard rules.

        Returns: (should_close, reason)
        """
        if symbol not in self.positions:
            return False, "Position not tracked"

        pos = self.positions[symbol]
        now = datetime.now()

        # Calculate P/L percentage
        if pos.side == "LONG":
            pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100
        else:  # SHORT
            pnl_pct = ((pos.entry_price - current_price) / pos.entry_price) * 100

        # Calculate hold time
        hold_time = now - pos.entry_time
        hold_hours = hold_time.total_seconds() / 3600
        hold_minutes = hold_time.total_seconds() / 60

        # Update peak P/L for trailing stop
        if pnl_pct > pos.peak_pnl_pct:
            pos.peak_pnl_pct = pnl_pct

        # ========================================
        # RULE 1: TAKE PROFIT
        # ========================================
        if pnl_pct >= self.strategy.take_profit_pct:
            return True, f"TAKE PROFIT: +{pnl_pct:.2f}% >= +{self.strategy.take_profit_pct}%"

        # ========================================
        # RULE 2: STOP LOSS
        # ========================================
        if pnl_pct <= -self.strategy.stop_loss_pct:
            return True, f"STOP LOSS: {pnl_pct:.2f}% <= -{self.strategy.stop_loss_pct}%"

        # ========================================
        # RULE 3: TIME EXIT (Strategy A only)
        # ========================================
        if self.strategy.max_hold_hours is not None:
            if hold_hours >= self.strategy.max_hold_hours:
                return True, f"TIME EXIT: {hold_hours:.1f}h >= {self.strategy.max_hold_hours}h max (P/L: {pnl_pct:+.2f}%)"

        # ========================================
        # RULE 4: TRAILING STOP (Strategy B only)
        # ========================================
        if self.strategy.trailing_stop_enabled:
            # Activate trailing stop at threshold
            if pnl_pct >= self.strategy.trailing_stop_activation_pct:
                pos.trailing_active = True

            # If trailing is active, check if we've dropped too far from peak
            if pos.trailing_active:
                drawdown_from_peak = pos.peak_pnl_pct - pnl_pct
                if drawdown_from_peak >= self.strategy.trailing_stop_distance_pct:
                    return True, f"TRAILING STOP: Dropped {drawdown_from_peak:.2f}% from peak +{pos.peak_pnl_pct:.2f}%"

        # ========================================
        # RULE 5: TREND REVERSAL (both strategies)
        # ========================================
        if sma20 is not None and sma50 is not None and macd is not None:
            if pos.side == "LONG":
                # Long position in downtrend = close
                if sma20 < sma50 and macd < 0 and pnl_pct < 0:
                    return True, f"TREND REVERSAL (LONG): SMA20 < SMA50, MACD negative, P/L: {pnl_pct:+.2f}%"
            else:  # SHORT
                # Short position in uptrend = close
                if sma20 > sma50 and macd > 0 and pnl_pct < 0:
                    return True, f"TREND REVERSAL (SHORT): SMA20 > SMA50, MACD positive, P/L: {pnl_pct:+.2f}%"

        return False, "No exit trigger"

    def should_prevent_close(
        self,
        symbol: str,
        current_price: float,
    ) -> Tuple[bool, str]:
        """
        Check if LLM close request should be blocked.
        Only prevents if min hold time not met AND not at TP/SL.
        """
        if symbol not in self.positions:
            return False, "Position not tracked"

        pos = self.positions[symbol]
        now = datetime.now()

        # Calculate P/L
        if pos.side == "LONG":
            pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100
        else:
            pnl_pct = ((pos.entry_price - current_price) / pos.entry_price) * 100

        # Calculate hold time
        hold_minutes = (now - pos.entry_time).total_seconds() / 60

        # Check if at TP or SL
        at_target = pnl_pct >= self.strategy.take_profit_pct
        at_stop = pnl_pct <= -self.strategy.stop_loss_pct

        # Allow close if at TP/SL
        if at_target or at_stop:
            return False, "At TP/SL, close allowed"

        # Prevent close if min hold not met
        if hold_minutes < self.strategy.min_hold_minutes:
            return True, f"MIN HOLD: {hold_minutes:.1f}m < {self.strategy.min_hold_minutes}m (P/L: {pnl_pct:+.2f}%)"

        return False, "Close allowed"

    def can_open_new_trade(self) -> Tuple[bool, str]:
        """Check if we can open a new trade today"""
        if not self.daily_tracker.can_trade(self.strategy.max_trades_per_day):
            return False, f"DAILY LIMIT: {self.daily_tracker.trade_count}/{self.strategy.max_trades_per_day} trades today"
        return True, "Can trade"

    def get_position_status(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Get detailed status of a position"""
        if symbol not in self.positions:
            return {"error": "Position not tracked"}

        pos = self.positions[symbol]
        now = datetime.now()

        if pos.side == "LONG":
            pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100
        else:
            pnl_pct = ((pos.entry_price - current_price) / pos.entry_price) * 100

        hold_time = now - pos.entry_time

        return {
            "symbol": symbol,
            "side": pos.side,
            "strategy": pos.strategy,
            "entry_price": pos.entry_price,
            "current_price": current_price,
            "pnl_pct": pnl_pct,
            "peak_pnl_pct": pos.peak_pnl_pct,
            "trailing_active": pos.trailing_active,
            "hold_time": str(hold_time).split('.')[0],  # Remove microseconds
            "hold_hours": hold_time.total_seconds() / 3600,
            "tp_target": self.strategy.take_profit_pct,
            "sl_target": -self.strategy.stop_loss_pct,
            "max_hold": f"{self.strategy.max_hold_hours}h" if self.strategy.max_hold_hours else "Unlimited",
        }

    def get_daily_stats(self) -> Dict[str, Any]:
        """Get daily trading stats"""
        return {
            "date": self.daily_tracker.date,
            "trades_today": self.daily_tracker.trade_count,
            "max_trades": self.strategy.max_trades_per_day,
            "remaining": self.strategy.max_trades_per_day - self.daily_tracker.trade_count,
            "active_positions": len(self.positions),
        }
