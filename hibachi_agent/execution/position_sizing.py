"""
Intelligent Position Sizing Module
Adaptive sizing based on multiple factors: confidence, momentum, volatility, setup quality
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Intelligent position sizing that considers:
    - LLM confidence
    - Setup strength (indicator confluence)
    - Momentum (MACD strength)
    - Volatility (ATR-based risk adjustment)
    - Recent performance (win rate tracking)
    """

    def __init__(
        self,
        account_balance: float,
        max_positions: int = 15,
        reserve_pct: float = 0.15,
        min_size_usd: float = 10.0,
        sizing_mode: str = "adaptive"  # "conservative", "balanced", "aggressive", "adaptive"
    ):
        self.account_balance = account_balance
        self.max_positions = max_positions
        self.reserve_pct = reserve_pct
        self.min_size_usd = min_size_usd
        self.sizing_mode = sizing_mode

        # Calculate available capital
        self.available = account_balance * (1 - reserve_pct)
        self.base_position = self.available / max_positions

        # Track recent performance for adaptive sizing
        self.recent_wins = 0
        self.recent_losses = 0
        self.win_streak = 0
        self.loss_streak = 0

    def calculate_position_size(
        self,
        confidence: float,
        symbol: str,
        market_data: Optional[Dict] = None,
        decision_reasoning: Optional[str] = None
    ) -> Dict:
        """
        Calculate intelligent position size

        Args:
            confidence: LLM confidence (0.0-1.0)
            symbol: Trading symbol
            market_data: Dict with RSI, MACD, ATR, etc.
            decision_reasoning: LLM reasoning text for quality analysis

        Returns:
            Dict with size, multiplier, reasoning breakdown
        """

        # Start with base confidence multiplier
        base_multiplier = self._get_confidence_multiplier(confidence)

        # Apply additional factors
        momentum_adj = self._get_momentum_adjustment(market_data) if market_data else 1.0
        volatility_adj = self._get_volatility_adjustment(market_data) if market_data else 1.0
        quality_adj = self._get_setup_quality_adjustment(market_data, decision_reasoning)
        streak_adj = self._get_streak_adjustment()

        # Combined multiplier
        total_multiplier = base_multiplier * momentum_adj * volatility_adj * quality_adj * streak_adj

        # Cap multiplier within reason (0.5x to 3.0x base)
        total_multiplier = max(0.5, min(3.0, total_multiplier))

        # Calculate size
        calculated_size = self.base_position * total_multiplier

        # Apply minimum
        final_size = max(calculated_size, self.min_size_usd)

        # Safety: Don't exceed 20% of account on single position
        max_single_position = self.account_balance * 0.20
        if final_size > max_single_position:
            final_size = max_single_position
            logger.warning(f"Capping {symbol} position at {max_single_position:.2f} (20% of account)")

        return {
            'size_usd': final_size,
            'total_multiplier': total_multiplier,
            'base_multiplier': base_multiplier,
            'momentum_adj': momentum_adj,
            'volatility_adj': volatility_adj,
            'quality_adj': quality_adj,
            'streak_adj': streak_adj,
            'pct_of_account': (final_size / self.account_balance) * 100,
            'reasoning': self._format_sizing_reasoning(
                symbol, confidence, total_multiplier,
                momentum_adj, volatility_adj, quality_adj, streak_adj
            )
        }

    def _get_confidence_multiplier(self, confidence: float) -> float:
        """Base multiplier from LLM confidence"""

        if self.sizing_mode == "conservative":
            # Conservative: Tighter sizing, less variance
            if confidence < 0.5:    return 0.6
            elif confidence < 0.7:  return 0.8
            elif confidence < 0.85: return 1.0
            else:                   return 1.2

        elif self.sizing_mode == "aggressive":
            # Aggressive: Wider sizing range, reward high confidence more
            if confidence < 0.5:    return 0.5
            elif confidence < 0.7:  return 0.9
            elif confidence < 0.85: return 1.5
            else:                   return 2.2

        elif self.sizing_mode == "adaptive":
            # Adaptive: Moderate range, adjusts with other factors
            if confidence < 0.5:    return 0.7
            elif confidence < 0.7:  return 1.0
            elif confidence < 0.85: return 1.4
            else:                   return 1.8

        else:  # "balanced" (default)
            # Balanced: Similar to current but wider range
            if confidence < 0.5:    return 0.7
            elif confidence < 0.7:  return 1.0
            elif confidence < 0.85: return 1.3
            else:                   return 1.7

    def _get_momentum_adjustment(self, market_data: Dict) -> float:
        """
        Adjust size based on momentum strength
        Strong MACD = bigger size (let runners run)
        """
        if not market_data:
            return 1.0

        macd = market_data.get('macd_5m')
        if macd is None:
            return 1.0

        # MACD strength scoring (adjust ranges based on observed values)
        if abs(macd) < 0.1:
            return 0.9  # Weak momentum, reduce slightly
        elif abs(macd) < 0.5:
            return 1.0  # Moderate momentum
        elif abs(macd) < 1.5:
            return 1.15  # Strong momentum, increase 15%
        else:
            return 1.25  # Very strong momentum, increase 25% (let it run!)

    def _get_volatility_adjustment(self, market_data: Dict) -> float:
        """
        Adjust size based on ATR (volatility)
        High volatility = smaller size (risk management)
        Low volatility = larger size (more volume)
        """
        if not market_data:
            return 1.0

        atr_4h = market_data.get('atr_4h')
        current_price = market_data.get('current_price')

        if not atr_4h or not current_price:
            return 1.0

        # Calculate ATR as % of price (normalized volatility)
        atr_pct = (atr_4h / current_price) * 100

        # Volatility-based sizing
        if atr_pct < 2.0:
            return 1.2  # Low volatility, safe to size up
        elif atr_pct < 4.0:
            return 1.0  # Normal volatility
        elif atr_pct < 7.0:
            return 0.85  # High volatility, reduce size
        else:
            return 0.7  # Extreme volatility, significantly reduce

    def _get_setup_quality_adjustment(
        self,
        market_data: Optional[Dict],
        decision_reasoning: Optional[str]
    ) -> float:
        """
        Reward high-quality setups with confluence
        - Multiple indicators aligned
        - Strong reasoning citations
        """
        quality_score = 1.0

        if not market_data:
            return quality_score

        # Check indicator confluence
        indicators_aligned = 0
        total_indicators = 0

        # RSI alignment
        rsi = market_data.get('rsi_5m')
        if rsi:
            total_indicators += 1
            if rsi < 35 or rsi > 65:  # Clear oversold/overbought
                indicators_aligned += 1

        # MACD alignment
        macd = market_data.get('macd_5m')
        if macd:
            total_indicators += 1
            if abs(macd) > 0.3:  # Strong momentum
                indicators_aligned += 1

        # Stochastic alignment
        stoch_k = market_data.get('stoch_k')
        if stoch_k:
            total_indicators += 1
            if stoch_k < 25 or stoch_k > 75:  # Clear signal
                indicators_aligned += 1

        # ADX trend strength
        adx_4h = market_data.get('adx_4h')
        if adx_4h:
            total_indicators += 1
            if adx_4h > 25:  # Strong trend
                indicators_aligned += 1

        # Calculate confluence bonus
        if total_indicators >= 3:
            alignment_pct = indicators_aligned / total_indicators
            if alignment_pct >= 0.75:
                quality_score = 1.2  # 75%+ confluence = +20% size
            elif alignment_pct >= 0.5:
                quality_score = 1.1  # 50%+ confluence = +10% size

        # Bonus for detailed reasoning (V2 prompt quality)
        if decision_reasoning:
            # Check for exact citations (V2 quality marker)
            if "RSI" in decision_reasoning and any(char.isdigit() for char in decision_reasoning):
                quality_score *= 1.05  # +5% for citing actual values

        return quality_score

    def _get_streak_adjustment(self) -> float:
        """
        Adjust based on recent win/loss streaks
        Win streak = slightly larger (confidence building)
        Loss streak = smaller (risk management)
        """
        if self.win_streak >= 3:
            return 1.1  # 3+ wins, increase 10%
        elif self.win_streak >= 2:
            return 1.05  # 2 wins, increase 5%
        elif self.loss_streak >= 3:
            return 0.85  # 3+ losses, reduce 15%
        elif self.loss_streak >= 2:
            return 0.92  # 2 losses, reduce 8%
        else:
            return 1.0  # No clear streak

    def _format_sizing_reasoning(
        self,
        symbol: str,
        confidence: float,
        total_multiplier: float,
        momentum_adj: float,
        volatility_adj: float,
        quality_adj: float,
        streak_adj: float
    ) -> str:
        """Format human-readable sizing explanation"""

        factors = []
        if confidence >= 0.85:
            factors.append(f"high confidence ({confidence:.2f})")
        elif confidence < 0.6:
            factors.append(f"low confidence ({confidence:.2f})")

        if momentum_adj > 1.1:
            factors.append("strong momentum (+)")
        elif momentum_adj < 0.95:
            factors.append("weak momentum (-)")

        if volatility_adj < 0.9:
            factors.append("high volatility (-)")
        elif volatility_adj > 1.1:
            factors.append("low volatility (+)")

        if quality_adj > 1.1:
            factors.append("high confluence (+)")

        if streak_adj > 1.05:
            factors.append(f"win streak (+)")
        elif streak_adj < 0.95:
            factors.append(f"loss streak (-)")

        if factors:
            return f"{total_multiplier:.2f}x multiplier: {', '.join(factors)}"
        else:
            return f"{total_multiplier:.2f}x multiplier (baseline)"

    def update_performance(self, won: bool):
        """Update recent performance tracking"""
        if won:
            self.recent_wins += 1
            self.win_streak += 1
            self.loss_streak = 0
        else:
            self.recent_losses += 1
            self.loss_streak += 1
            self.win_streak = 0

        # Keep rolling window of last 20 trades
        if self.recent_wins + self.recent_losses > 20:
            # Reset counters (could be more sophisticated with deque)
            self.recent_wins = max(10, self.recent_wins - 5)
            self.recent_losses = max(10, self.recent_losses - 5)


# Quick sizing mode presets
SIZING_MODES = {
    "conservative": {
        "description": "Tight sizing range, lower risk",
        "confidence_range": "0.6x-1.2x",
        "max_multiplier": 2.0,
        "use_case": "Small account or risk-averse"
    },
    "balanced": {
        "description": "Moderate sizing range, balanced risk/reward",
        "confidence_range": "0.7x-1.7x",
        "max_multiplier": 2.5,
        "use_case": "Default recommended mode"
    },
    "aggressive": {
        "description": "Wide sizing range, higher risk/reward",
        "confidence_range": "0.5x-2.2x",
        "max_multiplier": 3.0,
        "use_case": "Larger account, experienced"
    },
    "adaptive": {
        "description": "Adjusts to market conditions and performance",
        "confidence_range": "0.7x-1.8x + dynamic adjustments",
        "max_multiplier": 3.0,
        "use_case": "Best for varying conditions"
    }
}
