"""
Performance Analyzer - Analyzes trading performance and generates recommendations

This component takes rolling statistics from the OutcomeTracker and determines:
1. Overall accuracy of direction calls
2. Which direction bias (ETH vs BTC) is performing better
3. Whether the strategy needs adjustment
4. Specific recommendations for the StrategyAdjuster

Exchange-agnostic: Works with standardized statistics.
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Recommendation(Enum):
    """Possible recommendations from the analyzer"""
    HOLD_STEADY = "hold_steady"           # Strategy is working well
    INCREASE_ETH_BIAS = "increase_eth_bias"  # ETH calls doing better
    INCREASE_BTC_BIAS = "increase_btc_bias"  # BTC calls doing better
    INSUFFICIENT_DATA = "insufficient_data"   # Not enough trades to analyze
    NEUTRAL = "neutral"                    # No clear signal either way


@dataclass
class AnalysisResult:
    """Result of performance analysis"""
    accuracy: float
    sample_size: int
    recommendation: Recommendation
    suggested_bias: float  # 0.0 = full ETH, 0.5 = neutral, 1.0 = full BTC
    reasoning: str
    eth_accuracy: float
    btc_accuracy: float
    avg_spread_return: float
    confidence: float  # How confident we are in this recommendation


class PerformanceAnalyzer:
    """
    Analyzes trading performance and generates strategy recommendations.

    The analyzer looks at rolling statistics and determines if the LLM
    is consistently making wrong direction calls. It provides recommendations
    for adjusting the strategy bias.

    Thresholds:
    - ACCURACY_TERRIBLE (0.35): Below this, something is very wrong
    - ACCURACY_BAD (0.45): Below this, needs adjustment
    - ACCURACY_GOOD (0.55): Above this, strategy is working
    - MIN_TRADES (5): Minimum trades for valid analysis

    Usage:
        analyzer = PerformanceAnalyzer()

        stats = outcome_tracker.get_rolling_stats(n=10)
        result = analyzer.analyze(stats)

        if result.recommendation == Recommendation.INCREASE_BTC_BIAS:
            # Adjust strategy to favor BTC
            pass
    """

    # Accuracy thresholds
    ACCURACY_TERRIBLE = 0.35   # Below this = major problem
    ACCURACY_BAD = 0.45        # Below this = needs adjustment
    ACCURACY_GOOD = 0.55       # Above this = working well
    MIN_TRADES = 5             # Minimum trades for valid analysis

    # Bias calculation parameters
    BIAS_DIFFERENCE_THRESHOLD = 0.15  # Min difference to suggest bias change

    def __init__(self):
        """Initialize the analyzer"""
        logger.info("PerformanceAnalyzer initialized")
        logger.info(f"  Accuracy thresholds: terrible={self.ACCURACY_TERRIBLE}, "
                   f"bad={self.ACCURACY_BAD}, good={self.ACCURACY_GOOD}")

    def analyze(self, stats: Dict) -> AnalysisResult:
        """
        Analyze rolling statistics and generate recommendation.

        Args:
            stats: Rolling statistics from OutcomeTracker.get_rolling_stats()
                   Expected keys: total, correct, accuracy, eth_bias, btc_bias,
                                 avg_spread_return, sufficient_data

        Returns:
            AnalysisResult with recommendation and reasoning
        """
        total = stats.get("total", 0)
        accuracy = stats.get("accuracy", 0.0)
        eth_bias = stats.get("eth_bias", {})
        btc_bias = stats.get("btc_bias", {})
        avg_spread = stats.get("avg_spread_return", 0.0)

        eth_accuracy = eth_bias.get("accuracy", 0.0)
        btc_accuracy = btc_bias.get("accuracy", 0.0)
        eth_count = eth_bias.get("count", 0)
        btc_count = btc_bias.get("count", 0)

        # Check for insufficient data
        if total < self.MIN_TRADES:
            return AnalysisResult(
                accuracy=accuracy,
                sample_size=total,
                recommendation=Recommendation.INSUFFICIENT_DATA,
                suggested_bias=0.5,  # Stay neutral
                reasoning=f"Only {total} trades, need at least {self.MIN_TRADES} for analysis",
                eth_accuracy=eth_accuracy,
                btc_accuracy=btc_accuracy,
                avg_spread_return=avg_spread,
                confidence=0.0
            )

        # Calculate suggested bias based on relative performance
        suggested_bias = self._calculate_suggested_bias(
            eth_accuracy, btc_accuracy, eth_count, btc_count
        )

        # Determine recommendation
        recommendation, reasoning, confidence = self._determine_recommendation(
            accuracy, eth_accuracy, btc_accuracy, eth_count, btc_count, avg_spread
        )

        result = AnalysisResult(
            accuracy=accuracy,
            sample_size=total,
            recommendation=recommendation,
            suggested_bias=suggested_bias,
            reasoning=reasoning,
            eth_accuracy=eth_accuracy,
            btc_accuracy=btc_accuracy,
            avg_spread_return=avg_spread,
            confidence=confidence
        )

        # Log the analysis
        self._log_analysis(result)

        return result

    def _calculate_suggested_bias(
        self,
        eth_accuracy: float,
        btc_accuracy: float,
        eth_count: int,
        btc_count: int
    ) -> float:
        """
        Calculate suggested bias based on accuracy difference.

        Returns:
            Float from 0.0 (favor ETH) to 1.0 (favor BTC), 0.5 = neutral
        """
        # If no data for one side, stay closer to neutral
        if eth_count == 0 and btc_count == 0:
            return 0.5

        if eth_count == 0:
            # Only BTC data - if BTC is doing well, lean BTC; otherwise neutral
            return 0.6 if btc_accuracy > 0.5 else 0.5

        if btc_count == 0:
            # Only ETH data - if ETH is doing well, lean ETH; otherwise neutral
            return 0.4 if eth_accuracy > 0.5 else 0.5

        # Both have data - calculate weighted bias
        accuracy_diff = btc_accuracy - eth_accuracy

        # If difference is small, stay neutral
        if abs(accuracy_diff) < self.BIAS_DIFFERENCE_THRESHOLD:
            return 0.5

        # Scale the bias based on accuracy difference
        # Max adjustment of 0.3 from neutral (so range is 0.2 to 0.8)
        bias_adjustment = min(0.3, abs(accuracy_diff) / 2)

        if accuracy_diff > 0:
            # BTC is doing better, bias toward BTC
            return 0.5 + bias_adjustment
        else:
            # ETH is doing better, bias toward ETH
            return 0.5 - bias_adjustment

    def _determine_recommendation(
        self,
        accuracy: float,
        eth_accuracy: float,
        btc_accuracy: float,
        eth_count: int,
        btc_count: int,
        avg_spread: float
    ) -> tuple:
        """
        Determine the recommendation based on performance metrics.

        Returns:
            (Recommendation, reasoning_string, confidence)
        """
        # Case 1: Accuracy is good - hold steady
        if accuracy >= self.ACCURACY_GOOD:
            return (
                Recommendation.HOLD_STEADY,
                f"Accuracy {accuracy:.0%} is good. Strategy is working.",
                0.8
            )

        # Case 2: Accuracy is terrible - need to change something
        if accuracy < self.ACCURACY_TERRIBLE:
            # Which direction is worse?
            if eth_count > btc_count and eth_accuracy < self.ACCURACY_TERRIBLE:
                return (
                    Recommendation.INCREASE_BTC_BIAS,
                    f"Accuracy {accuracy:.0%} is terrible. ETH calls at {eth_accuracy:.0%} "
                    f"({eth_count} trades). Try longing BTC more.",
                    0.9
                )
            elif btc_count > eth_count and btc_accuracy < self.ACCURACY_TERRIBLE:
                return (
                    Recommendation.INCREASE_ETH_BIAS,
                    f"Accuracy {accuracy:.0%} is terrible. BTC calls at {btc_accuracy:.0%} "
                    f"({btc_count} trades). Try longing ETH more.",
                    0.9
                )
            else:
                # Both are bad or similar - suggest opposite of most tried
                if eth_count >= btc_count:
                    return (
                        Recommendation.INCREASE_BTC_BIAS,
                        f"Accuracy {accuracy:.0%} is terrible. Tried ETH {eth_count} times. "
                        f"Switch to BTC bias.",
                        0.7
                    )
                else:
                    return (
                        Recommendation.INCREASE_ETH_BIAS,
                        f"Accuracy {accuracy:.0%} is terrible. Tried BTC {btc_count} times. "
                        f"Switch to ETH bias.",
                        0.7
                    )

        # Case 3: Accuracy is bad but not terrible - moderate adjustment
        if accuracy < self.ACCURACY_BAD:
            accuracy_diff = btc_accuracy - eth_accuracy

            if accuracy_diff > self.BIAS_DIFFERENCE_THRESHOLD:
                return (
                    Recommendation.INCREASE_BTC_BIAS,
                    f"Accuracy {accuracy:.0%} needs improvement. BTC calls ({btc_accuracy:.0%}) "
                    f"outperforming ETH ({eth_accuracy:.0%}). Lean toward BTC.",
                    0.6
                )
            elif accuracy_diff < -self.BIAS_DIFFERENCE_THRESHOLD:
                return (
                    Recommendation.INCREASE_ETH_BIAS,
                    f"Accuracy {accuracy:.0%} needs improvement. ETH calls ({eth_accuracy:.0%}) "
                    f"outperforming BTC ({btc_accuracy:.0%}). Lean toward ETH.",
                    0.6
                )
            else:
                return (
                    Recommendation.NEUTRAL,
                    f"Accuracy {accuracy:.0%} is suboptimal, but no clear direction signal. "
                    f"ETH: {eth_accuracy:.0%}, BTC: {btc_accuracy:.0%}.",
                    0.4
                )

        # Case 4: Accuracy is between BAD and GOOD - hold steady but monitor
        return (
            Recommendation.HOLD_STEADY,
            f"Accuracy {accuracy:.0%} is acceptable. Continue current approach. "
            f"ETH: {eth_accuracy:.0%}, BTC: {btc_accuracy:.0%}.",
            0.5
        )

    def _log_analysis(self, result: AnalysisResult):
        """Log the analysis result"""
        logger.info("=" * 60)
        logger.info("PERFORMANCE ANALYSIS")
        logger.info("=" * 60)
        logger.info(f"  Sample size: {result.sample_size} trades")
        logger.info(f"  Overall accuracy: {result.accuracy:.1%}")
        logger.info(f"  ETH bias accuracy: {result.eth_accuracy:.1%}")
        logger.info(f"  BTC bias accuracy: {result.btc_accuracy:.1%}")
        logger.info(f"  Avg spread return: {result.avg_spread_return:+.2f}%")
        logger.info(f"  Recommendation: {result.recommendation.value}")
        logger.info(f"  Suggested bias: {result.suggested_bias:.2f}")
        logger.info(f"  Confidence: {result.confidence:.1%}")
        logger.info(f"  Reasoning: {result.reasoning}")
        logger.info("=" * 60)

    def should_trigger_adjustment(self, result: AnalysisResult) -> bool:
        """
        Determine if the analysis result should trigger a strategy adjustment.

        Args:
            result: AnalysisResult from analyze()

        Returns:
            True if adjustment is recommended
        """
        # Don't adjust if insufficient data
        if result.recommendation == Recommendation.INSUFFICIENT_DATA:
            return False

        # Don't adjust if holding steady
        if result.recommendation == Recommendation.HOLD_STEADY:
            return False

        # Don't adjust if neutral with low confidence
        if result.recommendation == Recommendation.NEUTRAL and result.confidence < 0.5:
            return False

        # Trigger adjustment for bias changes
        return result.recommendation in [
            Recommendation.INCREASE_ETH_BIAS,
            Recommendation.INCREASE_BTC_BIAS
        ]
