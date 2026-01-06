"""
Strategy G: Low-Liquidity Momentum Hunter

Designed for newer/lower-liquidity pairs on Hibachi DEX where:
- Retail hasn't priced in moves yet
- Volatility creates opportunities
- Fees matter less due to larger moves

Based on Qwen consultation:
- 2-hour max hold (not 4h - too risky for low-liq)
- -2% stop with trailing after +1.5%
- +3% take profit target
- 25-trade rolling window for self-learning
- VWAP + volume spike signals

Target pairs (avoid BTC/ETH - too efficient):
Tier 1: HYPE, PUMP, VIRTUAL, ENA, PROVE, XPL
Tier 2: DOGE, SEI, SUI, BNB
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class StrategyGLowLiqHunter:
    """
    Low-Liquidity Momentum Hunter Strategy

    Features:
    1. Focus on volatile low-liq pairs
    2. Strict exit rules (2h max, -2% stop, trailing stop)
    3. Self-learning signal weights
    4. VWAP-based entry confirmation
    """

    STRATEGY_NAME = "STRATEGY_G_LOW_LIQ_HUNTER"

    # Target low-liquidity pairs
    TIER_1_PAIRS = ["HYPE/USDT-P", "PUMP/USDT-P", "VIRTUAL/USDT-P", "ENA/USDT-P", "PROVE/USDT-P", "XPL/USDT-P"]
    TIER_2_PAIRS = ["DOGE/USDT-P", "SEI/USDT-P", "SUI/USDT-P", "BNB/USDT-P", "ZEC/USDT-P", "XRP/USDT-P"]

    # Avoid majors - too efficient, retail priced in
    AVOID_PAIRS = ["BTC/USDT-P", "ETH/USDT-P", "SOL/USDT-P"]

    def __init__(
        self,
        position_size: float = 15.0,  # $15 base (small for volatile pairs)
        max_positions: int = 3,  # Focus, not spray
        max_hold_minutes: int = 120,  # 2 hours max (Qwen recommendation)
        stop_loss_pct: float = -2.0,  # -2% stop (allow breathing room)
        take_profit_pct: float = 3.0,  # +3% target
        trailing_trigger_pct: float = 1.5,  # Start trailing after +1.5%
        trailing_stop_pct: float = 0.75,  # Trail at 0.75% behind high
        rolling_window: int = 25,  # Trades for learning (Qwen: 20-30)
        state_file: str = "logs/strategies/strategy_g_state.json"
    ):
        self.position_size = position_size
        self.max_positions = max_positions
        self.max_hold_minutes = max_hold_minutes
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_trigger_pct = trailing_trigger_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.rolling_window = rolling_window
        self.state_file = Path(state_file)

        # Signal weights (self-learning adjusts these)
        self.signal_weights = {
            'rsi': 1.0,
            'macd': 1.0,
            'volume_spike': 1.0,
            'ema_cross': 1.0,
            'vwap': 1.0,
            'funding_extreme': 1.0
        }

        # Track signal performance
        self.signal_outcomes = defaultdict(lambda: {'wins': 0, 'losses': 0})

        # Track trade high water marks for trailing stops
        self.position_high_marks = {}  # symbol -> highest pnl%

        # Daily loss tracking
        self.daily_loss = 0.0
        self.daily_loss_limit = -20.0  # Stop trading if down $20 in a day
        self.last_reset_date = datetime.now().date()

        # Load state
        self._load_state()

        logger.info(f"🎯 Strategy G: Low-Liq Hunter initialized")
        logger.info(f"   Targets: {len(self.TIER_1_PAIRS)} Tier 1, {len(self.TIER_2_PAIRS)} Tier 2 pairs")
        logger.info(f"   Exits: {max_hold_minutes}min max, {stop_loss_pct}% SL, +{take_profit_pct}% TP")

    def _load_state(self):
        """Load saved state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    self.signal_weights = state.get('signal_weights', self.signal_weights)
                    self.signal_outcomes = defaultdict(
                        lambda: {'wins': 0, 'losses': 0},
                        state.get('signal_outcomes', {})
                    )
                    self.daily_loss = state.get('daily_loss', 0.0)
                    logger.info(f"✅ Loaded Strategy G state from {self.state_file}")
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

    def _save_state(self):
        """Save state to file"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            state = {
                'signal_weights': self.signal_weights,
                'signal_outcomes': dict(self.signal_outcomes),
                'daily_loss': self.daily_loss,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def get_target_symbols(self) -> List[str]:
        """Get list of symbols to trade (excludes majors)"""
        return self.TIER_1_PAIRS + self.TIER_2_PAIRS

    def is_allowed_symbol(self, symbol: str) -> bool:
        """Check if symbol is in our target list"""
        return symbol in self.TIER_1_PAIRS or symbol in self.TIER_2_PAIRS

    def calculate_entry_score(self, market_data: Dict) -> Tuple[float, List[str]]:
        """
        Calculate entry score based on weighted signals

        Args:
            market_data: Dict with RSI, MACD, volume, EMA, VWAP, funding

        Returns:
            (score, list of triggered signals)
        """
        score = 0.0
        signals = []

        rsi = market_data.get('rsi', 50)
        macd = market_data.get('macd', 0)
        macd_signal = market_data.get('macd_signal', 0)
        volume_ratio = market_data.get('volume_ratio', 1.0)  # Current/avg volume
        price = market_data.get('price', 0)
        ema20 = market_data.get('ema20', price)
        vwap = market_data.get('vwap', price)
        funding = market_data.get('funding_rate', 0)

        # For longs
        side = market_data.get('side', 'long')

        if side == 'long':
            # RSI oversold bounce
            if rsi < 35:
                score += self.signal_weights['rsi']
                signals.append(f"RSI oversold ({rsi:.0f})")

            # MACD bullish
            if macd > macd_signal and macd > -50:
                score += self.signal_weights['macd']
                signals.append("MACD bullish")

            # Volume spike
            if volume_ratio > 2.0:
                score += self.signal_weights['volume_spike']
                signals.append(f"Volume spike ({volume_ratio:.1f}x)")

            # Price above EMA20
            if price > ema20:
                score += self.signal_weights['ema_cross']
                signals.append("Above EMA20")

            # Price near/below VWAP (good entry)
            if price <= vwap * 1.005:  # Within 0.5% of VWAP
                score += self.signal_weights['vwap']
                signals.append("Near VWAP")

            # Extreme negative funding (contrarian long)
            if funding < -0.03:  # Very negative = shorts overleveraged
                score += self.signal_weights['funding_extreme']
                signals.append(f"Funding contrarian ({funding:.3f}%)")

        else:  # shorts
            if rsi > 65:
                score += self.signal_weights['rsi']
                signals.append(f"RSI overbought ({rsi:.0f})")

            if macd < macd_signal and macd < 50:
                score += self.signal_weights['macd']
                signals.append("MACD bearish")

            if volume_ratio > 2.0:
                score += self.signal_weights['volume_spike']
                signals.append(f"Volume spike ({volume_ratio:.1f}x)")

            if price < ema20:
                score += self.signal_weights['ema_cross']
                signals.append("Below EMA20")

            if price >= vwap * 0.995:
                score += self.signal_weights['vwap']
                signals.append("Near VWAP")

            if funding > 0.05:  # Very positive = longs overleveraged
                score += self.signal_weights['funding_extreme']
                signals.append(f"Funding contrarian ({funding:.3f}%)")

        return score, signals

    def should_enter(self, symbol: str, market_data: Dict, current_positions: int) -> Tuple[bool, str]:
        """
        Determine if we should enter a trade

        Returns:
            (should_enter, reason)
        """
        # Check daily loss limit
        if self._check_daily_reset():
            pass  # Reset happened

        if self.daily_loss <= self.daily_loss_limit:
            return False, f"Daily loss limit hit (${self.daily_loss:.2f})"

        # Check symbol is in our target list
        if not self.is_allowed_symbol(symbol):
            return False, f"Not a target symbol (avoiding majors)"

        # Check position limit
        if current_positions >= self.max_positions:
            return False, f"Max positions reached ({self.max_positions})"

        # Calculate entry score
        score, signals = self.calculate_entry_score(market_data)

        # Need at least 3 signals (or 2 if on hot streak)
        min_signals = 3
        if self._is_hot_streak():
            min_signals = 2

        if score >= min_signals:
            return True, f"Entry score {score:.1f} with signals: {', '.join(signals)}"
        else:
            return False, f"Score {score:.1f} < {min_signals} minimum"

    def check_exit(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        entry_time: datetime,
        side: str = 'long'
    ) -> Tuple[bool, str, float]:
        """
        Check if position should be exited

        Returns:
            (should_exit, reason, pnl_pct)
        """
        # Guard against invalid entry_price
        if entry_price <= 0:
            logger.warning(f"Invalid entry_price {entry_price} for {symbol}, skipping exit check")
            return False, None, 0.0

        # Calculate P&L
        if side.lower() in ['long', 'buy']:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

        # Update high water mark for trailing stop
        if symbol not in self.position_high_marks:
            self.position_high_marks[symbol] = pnl_pct
        else:
            self.position_high_marks[symbol] = max(self.position_high_marks[symbol], pnl_pct)

        high_mark = self.position_high_marks[symbol]

        # 1. Hard stop loss
        if pnl_pct <= self.stop_loss_pct:
            return True, f"STOP LOSS: {pnl_pct:.2f}%", pnl_pct

        # 2. Take profit
        if pnl_pct >= self.take_profit_pct:
            return True, f"TAKE PROFIT: {pnl_pct:.2f}%", pnl_pct

        # 3. Trailing stop (after hitting trigger)
        if high_mark >= self.trailing_trigger_pct:
            trailing_stop = high_mark - self.trailing_stop_pct
            if pnl_pct <= trailing_stop:
                return True, f"TRAILING STOP: {pnl_pct:.2f}% (was +{high_mark:.2f}%)", pnl_pct

        # 4. Time exit
        age_minutes = (datetime.now() - entry_time).total_seconds() / 60
        if age_minutes >= self.max_hold_minutes:
            return True, f"TIME EXIT: {age_minutes:.0f}min (P&L: {pnl_pct:.2f}%)", pnl_pct

        return False, "", pnl_pct

    def record_trade_result(
        self,
        symbol: str,
        side: str,
        pnl: float,
        signals_used: List[str]
    ):
        """
        Record trade outcome for self-learning

        Args:
            symbol: Trading symbol
            side: 'long' or 'short'
            pnl: P&L in USD
            signals_used: List of signal names that triggered entry
        """
        # Update daily loss
        self.daily_loss += pnl

        # Clear high water mark
        if symbol in self.position_high_marks:
            del self.position_high_marks[symbol]

        # Record outcome for each signal
        is_win = pnl > 0
        for signal in signals_used:
            # Extract signal type from string (e.g., "RSI oversold (32)" -> "rsi")
            signal_type = self._extract_signal_type(signal)
            if signal_type:
                if is_win:
                    self.signal_outcomes[signal_type]['wins'] += 1
                else:
                    self.signal_outcomes[signal_type]['losses'] += 1

        # Check if we need to adjust weights
        total_trades = sum(
            o['wins'] + o['losses']
            for o in self.signal_outcomes.values()
        ) // len(self.signal_weights)  # Approximate trades

        if total_trades >= self.rolling_window and total_trades % 5 == 0:
            self._adjust_signal_weights()

        self._save_state()

        logger.info(f"📊 Recorded trade: {symbol} {side} ${pnl:.2f} | Daily: ${self.daily_loss:.2f}")

    def _extract_signal_type(self, signal_str: str) -> Optional[str]:
        """Extract signal type from signal string"""
        signal_lower = signal_str.lower()
        if 'rsi' in signal_lower:
            return 'rsi'
        elif 'macd' in signal_lower:
            return 'macd'
        elif 'volume' in signal_lower:
            return 'volume_spike'
        elif 'ema' in signal_lower:
            return 'ema_cross'
        elif 'vwap' in signal_lower:
            return 'vwap'
        elif 'funding' in signal_lower:
            return 'funding_extreme'
        return None

    def _adjust_signal_weights(self):
        """
        Adjust signal weights based on performance

        Per Qwen: Increase weight if win rate > 60%, decrease if < 40%
        """
        adjustments = []

        for signal, outcomes in self.signal_outcomes.items():
            total = outcomes['wins'] + outcomes['losses']
            if total < 5:
                continue

            win_rate = outcomes['wins'] / total
            current_weight = self.signal_weights.get(signal, 1.0)

            if win_rate > 0.6:
                # Good signal - increase weight (max 1.5)
                new_weight = min(1.5, current_weight * 1.1)
                adjustments.append(f"↑ {signal}: {win_rate:.0%} WR -> weight {new_weight:.2f}")
            elif win_rate < 0.4:
                # Bad signal - decrease weight (min 0.5)
                new_weight = max(0.5, current_weight * 0.9)
                adjustments.append(f"↓ {signal}: {win_rate:.0%} WR -> weight {new_weight:.2f}")
            else:
                new_weight = current_weight

            self.signal_weights[signal] = new_weight

        if adjustments:
            logger.info("🧠 SELF-LEARNING ADJUSTMENT:")
            for adj in adjustments:
                logger.info(f"   {adj}")

    def _is_hot_streak(self) -> bool:
        """Check if on a winning streak (reduce entry threshold)"""
        # Would need recent trade history - for now return False
        return False

    def _check_daily_reset(self) -> bool:
        """Reset daily loss if new day"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            logger.info(f"📅 New day - resetting daily loss (was ${self.daily_loss:.2f})")
            self.daily_loss = 0.0
            self.last_reset_date = today
            self._save_state()
            return True
        return False

    def get_prompt_context(self) -> str:
        """
        Generate context for LLM prompt

        Returns:
            String with strategy guidance and learned insights
        """
        lines = [
            "=" * 60,
            "🎯 STRATEGY G: LOW-LIQUIDITY MOMENTUM HUNTER",
            "=" * 60,
            "",
            "TARGET PAIRS (focus here, not majors):",
            f"  Tier 1 (most volatile): {', '.join([p.split('/')[0] for p in self.TIER_1_PAIRS])}",
            f"  Tier 2 (moderate): {', '.join([p.split('/')[0] for p in self.TIER_2_PAIRS])}",
            "",
            "AVOID: BTC, ETH, SOL (too efficient, retail priced in)",
            "",
            "ENTRY RULES (need 3+ signals):",
            "  - RSI < 35 (oversold long) or > 65 (overbought short)",
            "  - MACD crossing in trade direction",
            "  - Volume > 2x average (unusual activity)",
            "  - Price above/below EMA20",
            "  - Price near VWAP (good value)",
            "  - Extreme funding (contrarian signal)",
            "",
            f"EXIT RULES (STRICT):",
            f"  - STOP LOSS: {self.stop_loss_pct}% (no exceptions)",
            f"  - TAKE PROFIT: +{self.take_profit_pct}%",
            f"  - TRAILING: After +{self.trailing_trigger_pct}%, trail at {self.trailing_stop_pct}%",
            f"  - TIME: Max {self.max_hold_minutes} minutes",
            "",
        ]

        # Add learned insights
        if self.signal_outcomes:
            lines.append("📊 LEARNED SIGNAL PERFORMANCE:")
            for signal, outcomes in sorted(self.signal_outcomes.items()):
                total = outcomes['wins'] + outcomes['losses']
                if total >= 3:
                    wr = outcomes['wins'] / total
                    weight = self.signal_weights.get(signal, 1.0)
                    emoji = "✅" if wr > 0.5 else "⚠️"
                    lines.append(f"  {emoji} {signal}: {wr:.0%} win rate ({total} trades, weight: {weight:.1f})")

        lines.append("")
        lines.append(f"📈 Today's P&L: ${self.daily_loss:.2f} (limit: ${self.daily_loss_limit})")
        lines.append("=" * 60)

        return "\n".join(lines)


# Convenience function for testing
def create_strategy(**kwargs) -> StrategyGLowLiqHunter:
    """Create strategy with optional overrides"""
    return StrategyGLowLiqHunter(**kwargs)
