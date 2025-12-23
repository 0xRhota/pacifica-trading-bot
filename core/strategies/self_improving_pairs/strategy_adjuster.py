"""
Strategy Adjuster - Gradually adjusts strategy bias based on performance

This component takes recommendations from the PerformanceAnalyzer and
makes GRADUAL adjustments to the strategy bias. It never makes sudden
100% flips - instead it incrementally shifts the bias toward the
better-performing direction.

Key principles:
1. GRADUAL adjustment (max 0.15 per cycle)
2. Never go to extremes (clamp to [0.15, 0.85])
3. Log all adjustments with reasoning
4. Persist state across restarts

Exchange-agnostic: Works with any analysis results.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from .performance_analyzer import AnalysisResult, Recommendation

logger = logging.getLogger(__name__)


@dataclass
class AdjustmentRecord:
    """Record of a single bias adjustment"""
    timestamp: str
    old_bias: float
    new_bias: float
    recommendation: str
    reasoning: str
    accuracy_at_adjustment: float
    trade_count: int


class StrategyAdjuster:
    """
    Manages and adjusts strategy bias based on performance analysis.

    The bias value controls how the LLM prompt is constructed:
    - 0.0 = Always suggest longing ETH (extreme, never used)
    - 0.15-0.35 = Lean toward ETH
    - 0.35-0.65 = Neutral (let LLM decide freely)
    - 0.65-0.85 = Lean toward BTC
    - 1.0 = Always suggest longing BTC (extreme, never used)

    Adjustment rules:
    - Max adjustment per cycle: 0.15
    - Bias range: [0.15, 0.85]
    - Adjustments are logged for transparency

    Usage:
        adjuster = StrategyAdjuster()

        # Get current bias for prompt
        bias = adjuster.get_current_bias()
        instruction = adjuster.get_bias_instruction()

        # Apply adjustment from analysis
        analysis_result = analyzer.analyze(stats)
        adjuster.adjust(analysis_result, current_trade_count=15)

        # Get updated bias
        new_instruction = adjuster.get_bias_instruction()
    """

    STATE_FILE = "logs/strategies/self_improving_pairs_adjuster_state.json"

    # Bias limits (never go to extremes)
    MIN_BIAS = 0.15
    MAX_BIAS = 0.85
    NEUTRAL_BIAS = 0.50

    # Adjustment limits
    MAX_ADJUSTMENT_PER_CYCLE = 0.15  # Max change in one adjustment
    MIN_ADJUSTMENT = 0.05            # Don't bother with tiny changes

    def __init__(self, state_file: str = None):
        """
        Initialize the strategy adjuster.

        Args:
            state_file: Path to state persistence file
        """
        self.state_file = state_file or self.STATE_FILE
        self._state = self._load_or_create_state()

        # Ensure directory exists
        Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)

        logger.info("StrategyAdjuster initialized")
        logger.info(f"  Current bias: {self._state['current_bias']:.2f}")
        logger.info(f"  Adjustment history: {len(self._state['adjustments'])} records")

    def _load_or_create_state(self) -> Dict:
        """Load existing state or create new"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    if 'current_bias' in state and 'adjustments' in state:
                        return state
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Corrupted state file, creating new: {e}")

        # Create new state
        return {
            "current_bias": self.NEUTRAL_BIAS,
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "adjustments": [],
            "total_adjustments": 0
        }

    def _save_state(self):
        """Save state to disk"""
        try:
            self._state["last_updated"] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save adjuster state: {e}")

    def get_current_bias(self) -> float:
        """
        Get the current bias value.

        Returns:
            Float from 0.15 to 0.85
            - < 0.35: Lean ETH
            - 0.35-0.65: Neutral
            - > 0.65: Lean BTC
        """
        return self._state["current_bias"]

    def get_bias_instruction(self) -> str:
        """
        Get a human-readable instruction for the LLM prompt based on current bias.

        Returns:
            String instruction to include in the LLM prompt
        """
        bias = self._state["current_bias"]

        if bias < 0.25:
            return (
                "STRONG ETH BIAS: Past BTC calls have significantly underperformed. "
                "Strongly consider longing ETH unless data clearly contradicts this."
            )
        elif bias < 0.40:
            return (
                "LEAN ETH: Past performance suggests ETH calls tend to be more accurate. "
                "Consider favoring ETH, but override if data strongly suggests BTC."
            )
        elif bias <= 0.60:
            return (
                "NEUTRAL: No strong bias from past performance. "
                "Analyze current data freely and make your best judgment."
            )
        elif bias < 0.75:
            return (
                "LEAN BTC: Past performance suggests BTC calls tend to be more accurate. "
                "Consider favoring BTC, but override if data strongly suggests ETH."
            )
        else:
            return (
                "STRONG BTC BIAS: Past ETH calls have significantly underperformed. "
                "Strongly consider longing BTC unless data clearly contradicts this."
            )

    def get_suggested_direction(self) -> Optional[str]:
        """
        Get the suggested direction based on current bias.

        Returns:
            "ETH", "BTC", or None (if neutral)
        """
        bias = self._state["current_bias"]

        if bias < 0.40:
            return "ETH"
        elif bias > 0.60:
            return "BTC"
        else:
            return None  # Neutral

    def adjust(self, analysis: AnalysisResult, current_trade_count: int) -> float:
        """
        Apply adjustment based on analysis result.

        Args:
            analysis: AnalysisResult from PerformanceAnalyzer
            current_trade_count: Current total number of closed trades

        Returns:
            New bias value after adjustment
        """
        old_bias = self._state["current_bias"]

        # Determine target bias from analysis
        target_bias = analysis.suggested_bias

        # Calculate adjustment (limited by MAX_ADJUSTMENT_PER_CYCLE)
        adjustment_needed = target_bias - old_bias

        # Apply gradual adjustment
        if abs(adjustment_needed) < self.MIN_ADJUSTMENT:
            # Change is too small, don't bother
            logger.info(f"[ADJUSTER] No adjustment needed (change {adjustment_needed:.3f} < min {self.MIN_ADJUSTMENT})")
            return old_bias

        # Limit adjustment magnitude
        if adjustment_needed > 0:
            actual_adjustment = min(adjustment_needed, self.MAX_ADJUSTMENT_PER_CYCLE)
        else:
            actual_adjustment = max(adjustment_needed, -self.MAX_ADJUSTMENT_PER_CYCLE)

        # Calculate new bias
        new_bias = old_bias + actual_adjustment

        # Clamp to valid range
        new_bias = max(self.MIN_BIAS, min(self.MAX_BIAS, new_bias))

        # If no effective change after clamping, skip
        if abs(new_bias - old_bias) < 0.01:
            logger.info(f"[ADJUSTER] No effective change after clamping")
            return old_bias

        # Record the adjustment
        record = AdjustmentRecord(
            timestamp=datetime.now().isoformat(),
            old_bias=round(old_bias, 4),
            new_bias=round(new_bias, 4),
            recommendation=analysis.recommendation.value,
            reasoning=analysis.reasoning,
            accuracy_at_adjustment=analysis.accuracy,
            trade_count=current_trade_count
        )

        self._state["adjustments"].append(asdict(record))
        self._state["current_bias"] = round(new_bias, 4)
        self._state["total_adjustments"] += 1
        self._save_state()

        # Log the adjustment
        direction = "toward BTC" if new_bias > old_bias else "toward ETH"
        logger.info("=" * 60)
        logger.info("STRATEGY ADJUSTMENT")
        logger.info("=" * 60)
        logger.info(f"  Bias: {old_bias:.2f} → {new_bias:.2f} ({direction})")
        logger.info(f"  Reason: {analysis.reasoning}")
        logger.info(f"  Accuracy at adjustment: {analysis.accuracy:.1%}")
        logger.info(f"  Trade count: {current_trade_count}")
        logger.info(f"  New instruction: {self.get_bias_instruction()[:50]}...")
        logger.info("=" * 60)

        return new_bias

    def reset_to_neutral(self, reason: str = "Manual reset"):
        """
        Reset bias to neutral.

        Args:
            reason: Reason for the reset (logged)
        """
        old_bias = self._state["current_bias"]

        record = AdjustmentRecord(
            timestamp=datetime.now().isoformat(),
            old_bias=old_bias,
            new_bias=self.NEUTRAL_BIAS,
            recommendation="manual_reset",
            reasoning=reason,
            accuracy_at_adjustment=0.0,
            trade_count=0
        )

        self._state["adjustments"].append(asdict(record))
        self._state["current_bias"] = self.NEUTRAL_BIAS
        self._save_state()

        logger.info(f"[ADJUSTER] Reset to neutral: {old_bias:.2f} → {self.NEUTRAL_BIAS:.2f}")
        logger.info(f"[ADJUSTER] Reason: {reason}")

    def get_adjustment_history(self, n: int = 10) -> List[Dict]:
        """
        Get the last n adjustments.

        Args:
            n: Number of recent adjustments to return

        Returns:
            List of adjustment records
        """
        return self._state["adjustments"][-n:]

    def get_state_summary(self) -> Dict:
        """
        Get a summary of the current adjuster state.

        Returns:
            Dict with current bias, instruction, and stats
        """
        return {
            "current_bias": self._state["current_bias"],
            "bias_instruction": self.get_bias_instruction(),
            "suggested_direction": self.get_suggested_direction(),
            "total_adjustments": self._state["total_adjustments"],
            "last_updated": self._state["last_updated"],
            "bias_category": self._get_bias_category()
        }

    def _get_bias_category(self) -> str:
        """Get human-readable category for current bias"""
        bias = self._state["current_bias"]

        if bias < 0.25:
            return "STRONG_ETH"
        elif bias < 0.40:
            return "LEAN_ETH"
        elif bias <= 0.60:
            return "NEUTRAL"
        elif bias < 0.75:
            return "LEAN_BTC"
        else:
            return "STRONG_BTC"
