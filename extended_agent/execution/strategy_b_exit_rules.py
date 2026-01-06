"""
Strategy B Exit Rules - PROFIT FOCUSED (for Extended)
Updated 2026-01-06: Pivot from volume to profit-focused longer holds

KEY PARAMETERS:
- Take Profit: 8% (let winners run)
- Stop Loss: 4% (wider to avoid stop hunts)
- Max Hold: 48 HOURS (allow overnight/multi-day)
- Min Hold: 60 minutes (prevent panic exits)
- Trailing Stop: Activates at +3%, trails by 1.5%
- Max Trades/Day: 6 (quality over quantity)

NEW PHILOSOPHY (2026-01-06):
- Fees + spread = ~0.30% per trade on Extended, quick trades lose money
- Hold positions longer when confident, cut losers after 4h if underwater
- Synchronized with Hibachi via shared_learning.py
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class StrategyBExitRules:
    """
    PROFIT FOCUSED exit strategy - hold for 24-48 hours, let winners run.

    Philosophy: Quality trades with bigger targets > many small trades
    Math: 6 trades/day × 40% win rate × 2:1 R/R = sustainable profit

    v8 Update (2026-01-06): Pivot from volume to profit
    - Fees + spread grinding down edge on quick trades
    - Longer holds let winners develop, justify the fee drag
    - Synchronized with Hibachi via shared_learning.py
    """

    # Strategy constants - PROFIT FOCUSED (2026-01-06)
    STRATEGY_NAME = "STRATEGY_B_PROFIT_FOCUS"
    TAKE_PROFIT_PCT = 8.0      # +8% exit (let winners run)
    STOP_LOSS_PCT = 4.0        # -4% exit (wider to avoid stop hunts)
    MAX_HOLD_HOURS = 48.0      # 48 hour max (allow overnight/multi-day)
    MIN_HOLD_MINUTES = 60.0    # 60 min minimum (prevent panic exits)
    MAX_TRADES_PER_DAY = 6     # Quality over quantity

    # Trailing stop parameters (ENABLED)
    TRAILING_ACTIVATION_PCT = 3.0     # Activate at +3%
    TRAILING_DISTANCE_PCT = 1.5       # Trail 1.5% from peak

    def __init__(self):
        """Initialize Strategy B exit rules"""
        self.daily_trade_count = 0
        self.last_trade_date = datetime.now().strftime('%Y-%m-%d')
        self.position_entry_times: Dict[str, datetime] = {}
        self.position_peak_pnl: Dict[str, float] = {}  # Track peak P/L for trailing
        self.trailing_active: Dict[str, bool] = {}     # Track if trailing is active

        logger.info("=" * 60)
        logger.info(f"STRATEGY B: PROFIT FOCUSED")
        logger.info(f"  TP: +{self.TAKE_PROFIT_PCT}%  |  SL: -{self.STOP_LOSS_PCT}%")
        logger.info(f"  Max Hold: {self.MAX_HOLD_HOURS}h  |  Min Hold: {self.MIN_HOLD_MINUTES}min")
        logger.info(f"  Max Trades: {self.MAX_TRADES_PER_DAY}/day")
        logger.info(f"  Trailing: Activates +{self.TRAILING_ACTIVATION_PCT}%, trails {self.TRAILING_DISTANCE_PCT}%")
        logger.info(f"  Cut Losers: After 4h if underwater")
        logger.info("=" * 60)

    def _reset_daily_count_if_new_day(self):
        """Reset trade count at midnight"""
        today = datetime.now().strftime('%Y-%m-%d')
        if today != self.last_trade_date:
            logger.info(f"[STRATEGY-B] New day {today} - resetting trade count (was: {self.daily_trade_count})")
            self.daily_trade_count = 0
            self.last_trade_date = today

    def register_position(self, symbol: str) -> None:
        """Register a new position for tracking"""
        self._reset_daily_count_if_new_day()
        self.position_entry_times[symbol] = datetime.now()
        self.position_peak_pnl[symbol] = 0.0
        self.trailing_active[symbol] = False
        self.daily_trade_count += 1
        logger.info(f"[STRATEGY-B] Registered {symbol} | Trade #{self.daily_trade_count}/{self.MAX_TRADES_PER_DAY}")

    def unregister_position(self, symbol: str) -> None:
        """Unregister a position when closed"""
        if symbol in self.position_entry_times:
            del self.position_entry_times[symbol]
        if symbol in self.position_peak_pnl:
            del self.position_peak_pnl[symbol]
        if symbol in self.trailing_active:
            del self.trailing_active[symbol]
        logger.info(f"[STRATEGY-B] Unregistered {symbol}")

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

        # Update peak P/L for trailing stop
        if symbol not in self.position_peak_pnl:
            self.position_peak_pnl[symbol] = pnl_pct
        elif pnl_pct > self.position_peak_pnl[symbol]:
            self.position_peak_pnl[symbol] = pnl_pct

        peak_pnl = self.position_peak_pnl.get(symbol, 0)

        # ═══════════════════════════════════════════════════════════════
        # RULE 1: TAKE PROFIT (+8%)
        # ═══════════════════════════════════════════════════════════════
        if pnl_pct >= self.TAKE_PROFIT_PCT:
            logger.info("=" * 50)
            logger.info(f"🎯 [STRATEGY-B] TAKE PROFIT")
            logger.info(f"   Symbol: {symbol} ({side})")
            logger.info(f"   P/L: +{pnl_pct:.2f}% >= +{self.TAKE_PROFIT_PCT}% target")
            logger.info(f"   Hold time: {hold_hours:.2f}h")
            logger.info(f"   Peak P/L: +{peak_pnl:.2f}%")
            logger.info("=" * 50)
            return True, f"TAKE PROFIT: +{pnl_pct:.2f}%"

        # ═══════════════════════════════════════════════════════════════
        # RULE 2: STOP LOSS (-1%)
        # ═══════════════════════════════════════════════════════════════
        if pnl_pct <= -self.STOP_LOSS_PCT:
            logger.info("=" * 50)
            logger.info(f"🛑 [STRATEGY-B] STOP LOSS")
            logger.info(f"   Symbol: {symbol} ({side})")
            logger.info(f"   P/L: {pnl_pct:.2f}% <= -{self.STOP_LOSS_PCT}% stop")
            logger.info(f"   Hold time: {hold_hours:.2f}h")
            logger.info("=" * 50)
            return True, f"STOP LOSS: {pnl_pct:.2f}%"

        # ═══════════════════════════════════════════════════════════════
        # RULE 3: CUT LOSER EARLY (4 hours if underwater)
        # ═══════════════════════════════════════════════════════════════
        if hold_hours >= 4.0 and pnl_pct < 0:
            logger.info("=" * 50)
            logger.info(f"✂️  [STRATEGY-B] CUT LOSER")
            logger.info(f"   Symbol: {symbol} ({side})")
            logger.info(f"   Hold time: {hold_hours:.2f}h >= 4h AND losing")
            logger.info(f"   P/L: {pnl_pct:+.2f}%")
            logger.info("=" * 50)
            return True, f"CUT LOSER: {hold_hours:.2f}h underwater (P/L: {pnl_pct:+.2f}%)"

        # ═══════════════════════════════════════════════════════════════
        # RULE 4: TRAILING STOP - LET WINNERS RUN
        # ═══════════════════════════════════════════════════════════════
        # Check if trailing should activate
        if pnl_pct >= self.TRAILING_ACTIVATION_PCT:
            if not self.trailing_active.get(symbol, False):
                self.trailing_active[symbol] = True
                logger.info(f"🔔 [STRATEGY-B] TRAILING STOP ACTIVATED - {symbol}")
                logger.info(f"   P/L: +{pnl_pct:.2f}% >= +{self.TRAILING_ACTIVATION_PCT}% threshold")
                logger.info(f"   Will trail {self.TRAILING_DISTANCE_PCT}% from peak")

        # Check if trailing stop is hit
        if self.trailing_active.get(symbol, False):
            drawdown_from_peak = peak_pnl - pnl_pct
            trailing_trigger = self.TRAILING_DISTANCE_PCT

            if drawdown_from_peak >= trailing_trigger and pnl_pct > 0:
                logger.info("=" * 50)
                logger.info(f"📉 [STRATEGY-B] TRAILING STOP HIT")
                logger.info(f"   Symbol: {symbol} ({side})")
                logger.info(f"   Peak P/L: +{peak_pnl:.2f}%")
                logger.info(f"   Current P/L: +{pnl_pct:.2f}%")
                logger.info(f"   Drawdown: {drawdown_from_peak:.2f}% >= {trailing_trigger}% trail")
                logger.info(f"   Hold time: {hold_hours:.2f}h")
                logger.info("=" * 50)
                return True, f"TRAILING STOP: Peak +{peak_pnl:.2f}% → +{pnl_pct:.2f}%"

        # ═══════════════════════════════════════════════════════════════
        # RULE 3.5: TIME EXIT (Only if profitable +0.5%)
        # ═══════════════════════════════════════════════════════════════
        if self.MAX_HOLD_HOURS and hold_hours >= self.MAX_HOLD_HOURS:
            if pnl_pct >= 0.5:  # Only exit if +0.5% or better
                logger.info("=" * 50)
                logger.info(f"⏰ [STRATEGY-B] TIME EXIT (PROFITABLE)")
                logger.info(f"   Symbol: {symbol} ({side})")
                logger.info(f"   P/L: +{pnl_pct:.2f}% (> +0.5%)")
                logger.info(f"   Hold time: {hold_hours:.2f}h >= {self.MAX_HOLD_HOURS}h")
                logger.info("=" * 50)
                return True, f"TIME EXIT: {hold_hours:.2f}h (P/L: +{pnl_pct:.2f}%)"
            else:
                # Don't exit if losing - wait for stop or reversal
                logger.debug(f"[STRATEGY-B] {symbol} aged {hold_hours:.2f}h but unprofitable ({pnl_pct:+.2f}%) - waiting")

        # ═══════════════════════════════════════════════════════════════
        # NO FORCED TIME EXITS FOR LOSERS!
        # ═══════════════════════════════════════════════════════════════

        # ═══════════════════════════════════════════════════════════════
        # RULE 4: TREND REVERSAL (optional early exit for losers only)
        # ═══════════════════════════════════════════════════════════════
        if market_data and pnl_pct < 0:  # Only for losing positions
            rsi = market_data.get('rsi', 50)
            macd = market_data.get('macd', 0)
            sma20 = market_data.get('sma20')
            sma50 = market_data.get('sma50')

            # Strong trend reversal signals
            if side == 'LONG' and sma20 and sma50:
                if sma20 < sma50 and macd < 0 and rsi < 35:
                    logger.info(f"⚠️  [STRATEGY-B] TREND REVERSAL - {symbol} LONG")
                    logger.info(f"   SMA20 < SMA50, MACD {macd:.2f}, RSI {rsi:.1f}")
                    logger.info(f"   P/L: {pnl_pct:+.2f}%")
                    return True, f"TREND REVERSAL: Bearish crossover (P/L: {pnl_pct:+.2f}%)"

            elif side == 'SHORT' and sma20 and sma50:
                if sma20 > sma50 and macd > 0 and rsi > 65:
                    logger.info(f"⚠️  [STRATEGY-B] TREND REVERSAL - {symbol} SHORT")
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

        # Allow close if trailing stop is active and hit
        if self.trailing_active.get(symbol, False):
            peak_pnl = self.position_peak_pnl.get(symbol, 0)
            drawdown = peak_pnl - pnl_pct
            if drawdown >= self.TRAILING_DISTANCE_PCT and pnl_pct > 0:
                return False, "Trailing stop hit - close allowed"

        # Prevent close if under min hold
        if hold_minutes < self.MIN_HOLD_MINUTES:
            logger.info(f"🚫 [STRATEGY-B] PREVENTING CLOSE - {symbol}")
            logger.info(f"   Hold time: {hold_minutes:.1f}m < {self.MIN_HOLD_MINUTES}m minimum")
            logger.info(f"   P/L: {pnl_pct:+.2f}%")
            return True, f"Min hold not met: {hold_minutes:.1f}m < {self.MIN_HOLD_MINUTES}m"

        return False, "Close allowed"

    def get_status_summary(self) -> Dict:
        """Get current strategy status for logging"""
        self._reset_daily_count_if_new_day()

        # Build trailing status
        trailing_positions = [s for s, active in self.trailing_active.items() if active]

        return {
            "strategy": self.STRATEGY_NAME,
            "trades_today": self.daily_trade_count,
            "max_trades": self.MAX_TRADES_PER_DAY,
            "remaining": self.MAX_TRADES_PER_DAY - self.daily_trade_count,
            "active_positions": len(self.position_entry_times),
            "trailing_active": trailing_positions,
            "tp_target": f"+{self.TAKE_PROFIT_PCT}%",
            "sl_target": f"-{self.STOP_LOSS_PCT}%",
            "trailing_activation": f"+{self.TRAILING_ACTIVATION_PCT}%",
            "trailing_distance": f"{self.TRAILING_DISTANCE_PCT}%",
            "max_hold": "UNLIMITED",
        }

    def log_status(self) -> None:
        """Log current strategy status"""
        status = self.get_status_summary()
        logger.info("-" * 40)
        logger.info(f"[STRATEGY-B STATUS]")
        logger.info(f"  Trades today: {status['trades_today']}/{status['max_trades']}")
        logger.info(f"  Active positions: {status['active_positions']}")
        logger.info(f"  Trailing active: {status['trailing_active']}")
        logger.info(f"  Targets: TP {status['tp_target']}, SL {status['sl_target']}")
        logger.info(f"  Trailing: {status['trailing_activation']} → {status['trailing_distance']}")
        logger.info(f"  Max hold: {status['max_hold']}")
        logger.info("-" * 40)

    def log_position_status(self, symbol: str, pnl_pct: float) -> None:
        """Log detailed position status"""
        entry_time = self.position_entry_times.get(symbol)
        peak_pnl = self.position_peak_pnl.get(symbol, 0)
        is_trailing = self.trailing_active.get(symbol, False)

        hold_hours = 0.0
        if entry_time:
            hold_hours = (datetime.now() - entry_time).total_seconds() / 3600

        trailing_status = "ACTIVE" if is_trailing else "inactive"
        drawdown = peak_pnl - pnl_pct if peak_pnl > pnl_pct else 0

        logger.info(f"  [{symbol}] P/L: {pnl_pct:+.2f}% | Peak: +{peak_pnl:.2f}% | Hold: {hold_hours:.1f}h | Trail: {trailing_status}")
        if is_trailing:
            logger.info(f"    └─ Drawdown from peak: {drawdown:.2f}% (trigger: {self.TRAILING_DISTANCE_PCT}%)")
