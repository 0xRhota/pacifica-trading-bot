"""
Strategy A Exit Rules - TIME_CAPPED (for Hibachi)
Based on 2025-11-27 research / Qwen analysis
Updated 2025-12-08: Qwen v7 recommendations (widen SL, extend max hold)

KEY PARAMETERS:
- Take Profit: 4%
- Stop Loss: 2% (widened from 1% - stop hunting protection)
- Max Hold: 2 HOURS (extended from 1hr - let trades develop)
- Min Hold: 5 minutes
- Max Trades/Day: 20

This strategy prioritizes HIGH VOLUME over letting runners run.
v7 changes: Wider stops to avoid stop-hunting, longer holds to let trends develop
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class StrategyAExitRules:
    """
    TIME_CAPPED exit strategy - force close after 2 hours.

    Philosophy: Many small trades > few big trades
    Math: 20 trades/day × 25% win rate × 4:1 R/R = +3% daily

    v7 Update (2025-12-08): Widened SL to -2%, extended hold to 2hr
    Based on Qwen analysis: stop-hunting causing early exits on good setups
    """

    # Strategy constants
    STRATEGY_NAME = "STRATEGY_A_TIME_CAPPED"
    TAKE_PROFIT_PCT = 4.0      # +4% exit
    STOP_LOSS_PCT = 2.0        # -2% exit (widened from 1% - v7)
    MAX_HOLD_HOURS = 2.0       # 2 hour max (extended from 1hr - v7)
    MIN_HOLD_MINUTES = 5.0     # 5 min minimum
    MAX_TRADES_PER_DAY = 20

    def __init__(self):
        """Initialize Strategy A exit rules"""
        self.daily_trade_count = 0
        self.last_trade_date = datetime.now().strftime('%Y-%m-%d')
        self.position_entry_times: Dict[str, datetime] = {}

        logger.info("=" * 60)
        logger.info(f"STRATEGY A: TIME_CAPPED")
        logger.info(f"  TP: +{self.TAKE_PROFIT_PCT}%  |  SL: -{self.STOP_LOSS_PCT}%")
        logger.info(f"  Max Hold: {self.MAX_HOLD_HOURS} hour  |  Max Trades: {self.MAX_TRADES_PER_DAY}/day")
        logger.info("=" * 60)

    def _reset_daily_count_if_new_day(self):
        """Reset trade count at midnight"""
        today = datetime.now().strftime('%Y-%m-%d')
        if today != self.last_trade_date:
            logger.info(f"[STRATEGY-A] New day {today} - resetting trade count (was: {self.daily_trade_count})")
            self.daily_trade_count = 0
            self.last_trade_date = today

    def register_position(self, symbol: str) -> None:
        """Register a new position for tracking"""
        self._reset_daily_count_if_new_day()
        self.position_entry_times[symbol] = datetime.now()
        self.daily_trade_count += 1
        logger.info(f"[STRATEGY-A] Registered {symbol} | Trade #{self.daily_trade_count}/{self.MAX_TRADES_PER_DAY}")

    def unregister_position(self, symbol: str) -> None:
        """Unregister a position when closed"""
        if symbol in self.position_entry_times:
            del self.position_entry_times[symbol]
            logger.info(f"[STRATEGY-A] Unregistered {symbol}")

    def can_open_new_trade(self) -> Tuple[bool, str]:
        """Check if we can open a new trade today"""
        self._reset_daily_count_if_new_day()

        if self.daily_trade_count >= self.MAX_TRADES_PER_DAY:
            return False, f"Daily limit reached: {self.daily_trade_count}/{self.MAX_TRADES_PER_DAY}"

        remaining = self.MAX_TRADES_PER_DAY - self.daily_trade_count
        return True, f"Can trade ({remaining} remaining today)"

    def check_should_force_close(
        self,
        position: Dict,
        market_data: Dict,
        tracker_data: Optional[Dict] = None
    ) -> Tuple[bool, str]:
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
        pnl_pct = position.get('pnl_pct', 0)
        if isinstance(pnl_pct, (int, float)) and pnl_pct < 1 and pnl_pct > -1:
            pnl_pct = pnl_pct * 100  # Convert decimal to percentage

        # Get entry time
        entry_time = self.position_entry_times.get(symbol)
        if not entry_time and tracker_data:
            timestamp_str = tracker_data.get('timestamp')
            if timestamp_str:
                try:
                    entry_time = datetime.fromisoformat(timestamp_str)
                    self.position_entry_times[symbol] = entry_time
                except:
                    pass

        hold_hours = 0.0
        if entry_time:
            hold_time = datetime.now() - entry_time
            hold_hours = hold_time.total_seconds() / 3600

        # ═══════════════════════════════════════════════════════════════
        # RULE 1: TAKE PROFIT (+4%)
        # ═══════════════════════════════════════════════════════════════
        if pnl_pct >= self.TAKE_PROFIT_PCT:
            logger.info("=" * 50)
            logger.info(f"🎯 [STRATEGY-A] TAKE PROFIT")
            logger.info(f"   Symbol: {symbol} ({side})")
            logger.info(f"   P/L: +{pnl_pct:.2f}% >= +{self.TAKE_PROFIT_PCT}% target")
            logger.info(f"   Hold time: {hold_hours:.2f}h")
            logger.info("=" * 50)
            return True, f"TAKE PROFIT: +{pnl_pct:.2f}%"

        # ═══════════════════════════════════════════════════════════════
        # RULE 2: STOP LOSS (-1%)
        # ═══════════════════════════════════════════════════════════════
        if pnl_pct <= -self.STOP_LOSS_PCT:
            logger.info("=" * 50)
            logger.info(f"🛑 [STRATEGY-A] STOP LOSS")
            logger.info(f"   Symbol: {symbol} ({side})")
            logger.info(f"   P/L: {pnl_pct:.2f}% <= -{self.STOP_LOSS_PCT}% stop")
            logger.info(f"   Hold time: {hold_hours:.2f}h")
            logger.info("=" * 50)
            return True, f"STOP LOSS: {pnl_pct:.2f}%"

        # ═══════════════════════════════════════════════════════════════
        # RULE 3: TIME EXIT (1 HOUR MAX) - THE KEY DIFFERENTIATOR
        # ═══════════════════════════════════════════════════════════════
        if hold_hours >= self.MAX_HOLD_HOURS:
            logger.info("=" * 50)
            logger.info(f"⏰ [STRATEGY-A] TIME EXIT")
            logger.info(f"   Symbol: {symbol} ({side})")
            logger.info(f"   Hold time: {hold_hours:.2f}h >= {self.MAX_HOLD_HOURS}h max")
            logger.info(f"   Final P/L: {pnl_pct:+.2f}%")
            logger.info("=" * 50)
            return True, f"TIME EXIT: {hold_hours:.2f}h (P/L: {pnl_pct:+.2f}%)"

        # ═══════════════════════════════════════════════════════════════
        # RULE 4: TREND REVERSAL (optional early exit)
        # ═══════════════════════════════════════════════════════════════
        if market_data:
            rsi = market_data.get('rsi', 50)
            macd = market_data.get('macd', 0)
            sma20 = market_data.get('sma20')
            sma50 = market_data.get('sma50')

            # Strong trend reversal signals
            if side == 'LONG' and sma20 and sma50:
                if sma20 < sma50 and macd < 0 and rsi < 35:
                    logger.info(f"⚠️  [STRATEGY-A] TREND REVERSAL - {symbol} LONG")
                    logger.info(f"   SMA20 < SMA50, MACD {macd:.2f}, RSI {rsi:.1f}")
                    logger.info(f"   P/L: {pnl_pct:+.2f}%")
                    return True, f"TREND REVERSAL: Bearish crossover (P/L: {pnl_pct:+.2f}%)"

            elif side == 'SHORT' and sma20 and sma50:
                if sma20 > sma50 and macd > 0 and rsi > 65:
                    logger.info(f"⚠️  [STRATEGY-A] TREND REVERSAL - {symbol} SHORT")
                    logger.info(f"   SMA20 > SMA50, MACD {macd:.2f}, RSI {rsi:.1f}")
                    logger.info(f"   P/L: {pnl_pct:+.2f}%")
                    return True, f"TREND REVERSAL: Bullish crossover (P/L: {pnl_pct:+.2f}%)"

        # No exit trigger
        return False, ""

    def should_prevent_close(
        self,
        symbol: str,
        pnl_pct: float
    ) -> Tuple[bool, str]:
        """
        Check if LLM close request should be blocked (min hold not met)

        Args:
            symbol: The symbol to check
            pnl_pct: Current P/L percentage

        Returns:
            (should_prevent: bool, reason: str)
        """
        entry_time = self.position_entry_times.get(symbol)
        if not entry_time:
            return False, "Position not tracked"

        hold_minutes = (datetime.now() - entry_time).total_seconds() / 60

        # Allow close if at TP or SL
        if pnl_pct >= self.TAKE_PROFIT_PCT or pnl_pct <= -self.STOP_LOSS_PCT:
            return False, "At TP/SL - close allowed"

        # Prevent close if under min hold
        if hold_minutes < self.MIN_HOLD_MINUTES:
            logger.info(f"🚫 [STRATEGY-A] PREVENTING CLOSE - {symbol}")
            logger.info(f"   Hold time: {hold_minutes:.1f}m < {self.MIN_HOLD_MINUTES}m minimum")
            logger.info(f"   P/L: {pnl_pct:+.2f}%")
            return True, f"Min hold not met: {hold_minutes:.1f}m < {self.MIN_HOLD_MINUTES}m"

        return False, "Close allowed"

    def get_status_summary(self) -> Dict:
        """Get current strategy status for logging"""
        self._reset_daily_count_if_new_day()
        return {
            "strategy": self.STRATEGY_NAME,
            "trades_today": self.daily_trade_count,
            "max_trades": self.MAX_TRADES_PER_DAY,
            "remaining": self.MAX_TRADES_PER_DAY - self.daily_trade_count,
            "active_positions": len(self.position_entry_times),
            "tp_target": f"+{self.TAKE_PROFIT_PCT}%",
            "sl_target": f"-{self.STOP_LOSS_PCT}%",
            "max_hold": f"{self.MAX_HOLD_HOURS}h",
        }

    def log_status(self) -> None:
        """Log current strategy status"""
        status = self.get_status_summary()
        logger.info("-" * 40)
        logger.info(f"[STRATEGY-A STATUS]")
        logger.info(f"  Trades today: {status['trades_today']}/{status['max_trades']}")
        logger.info(f"  Active positions: {status['active_positions']}")
        logger.info(f"  Targets: TP {status['tp_target']}, SL {status['sl_target']}")
        logger.info(f"  Max hold: {status['max_hold']}")
        logger.info("-" * 40)
